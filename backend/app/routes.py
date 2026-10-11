import csv
import io
import json
import urllib.request
from datetime import date, datetime, timedelta, timezone

from flask import Blueprint, Response, current_app, request
from sqlalchemy import func, text

from .crud import register_crud
from .errors import ApiError, ok
from .extensions import db
from .models import (ACTION_STATUS, BLOCKER_STATUS, MISSION_STATUS, PRIORITIES, SPRINT_STATUS, STORY_STATUS, TASK_STATUS,
                     ActionItem, Activity, Blocker, Mission, Notification, ProgressSnapshot, Retrospective, Sprint, Task,
                     UserStory)
from .services import (check_due_dates, log_activity, notify, on_task_saved, record_snapshot)

api = Blueprint("api", __name__, url_prefix="/api")

S = lambda **k: {"type": "str", **k}
FK = lambda **k: {"type": "fk", **k}

# ---------------------------------------------------------------- health
@api.get("/health")
def health():
    try:
        db.session.execute(text("SELECT 1"))
        return ok({"status": "ok", "database": "connected", "time": datetime.now(timezone.utc).isoformat()})
    except Exception as e:  # genuine DB connectivity check
        db.session.rollback()
        return {"success": False, "data": {"status": "degraded", "database": "unreachable"},
                "error": {"message": "Database unreachable", "details": type(e).__name__}}, 503


@api.get("/health/live")
def liveness():
    """Process liveness only (no database access). Use /health for readiness."""
    return ok({"status": "alive"})


@api.get("/integrations/cicd")
def cicd_status():
    """Integration point for Part 2. Proxies a JSON status endpoint if CICD_STATUS_URL is configured."""
    url = current_app.config.get("CICD_STATUS_URL")
    if not url:
        return ok({"configured": False, "status": "not_configured",
                   "message": "No CI/CD provider connected yet. Set CICD_STATUS_URL to enable."})
    try:
        with urllib.request.urlopen(url, timeout=4) as r:  # noqa: S310 - operator-configured URL
            payload = json.loads(r.read().decode())
        return ok({"configured": True, "status": payload.get("status", "unknown"), "details": payload})
    except Exception as e:
        return ok({"configured": True, "status": "unreachable", "message": f"CI/CD status endpoint failed: {type(e).__name__}"})


# ---------------------------------------------------------------- missions
MISSION_SPEC = {"title": S(required=True, max=200), "description": S(), "priority": S(choices=PRIORITIES),
                "status": S(choices=MISSION_STATUS), "start_date": {"type": "date"}, "end_date": {"type": "date"}}


def mission_before(obj, old):
    if obj.start_date and obj.end_date and obj.end_date < obj.start_date:
        raise ApiError("Validation failed", 422, {"end_date": "must not be before start_date"})


register_crud(api, "missions", Mission, MISSION_SPEC, filters=("status", "priority"), search=("title", "description"),
              before_save=mission_before, label="Mission",
              after_save=lambda o, old, c: log_activity(f"Mission {'created' if c else 'updated'}: {o.title}", "mission", o.id),
              after_delete=lambda o, i: log_activity(f"Mission deleted: {i['title']}", "mission"))

# ---------------------------------------------------------------- sprints
SPRINT_SPEC = {"name": S(required=True, max=200), "goal": S(), "start_date": {"type": "date", "required": True},
               "end_date": {"type": "date", "required": True}}


def sprint_before(obj, old):
    if obj.end_date < obj.start_date:
        raise ApiError("Validation failed", 422, {"end_date": "must not be before start_date"})


register_crud(api, "sprints", Sprint, SPRINT_SPEC, filters=("status",), search=("name", "goal"), label="Sprint",
              order=[Sprint.start_date.desc(), Sprint.id.desc()], before_save=sprint_before,
              after_save=lambda o, old, c: log_activity(f"Sprint {'created' if c else 'updated'}: {o.name}", "sprint", o.id))


@api.post("/sprints/<int:id_>/start")
def start_sprint(id_):
    sprint = db.session.get(Sprint, id_) or _404("Sprint", id_)
    if sprint.status != "planned":
        raise ApiError(f"Only planned sprints can be started (this one is {sprint.status})", 409)
    if Sprint.query.filter_by(status="active").first():
        raise ApiError("Another sprint is already active. Complete it first.", 409)
    sprint.status, sprint.started_at = "active", datetime.now(timezone.utc)
    for st in sprint.stories:
        if st.status == "backlog":
            st.status = "in_sprint"
    db.session.flush()
    record_snapshot(sprint.id)
    log_activity(f"Sprint started: {sprint.name}", "sprint", sprint.id)
    notify("sprint_change", f"Sprint '{sprint.name}' has started", "sprint", sprint.id)
    db.session.commit()
    return ok(sprint.to_dict())


@api.post("/sprints/<int:id_>/complete")
def complete_sprint(id_):
    sprint = db.session.get(Sprint, id_) or _404("Sprint", id_)
    if sprint.status != "active":
        raise ApiError("Only active sprints can be completed", 409)
    body = request.get_json(silent=True) or {}
    carry_over = body.get("carry_over", True)
    db.session.flush()
    record_snapshot(sprint.id)
    total, done = sprint.points()
    sprint.committed_points, sprint.delivered_points = total, done
    sprint.status, sprint.completed_at = "completed", datetime.now(timezone.utc)
    moved = 0
    if carry_over:
        for st in sprint.stories.filter(UserStory.status != "done"):
            st.sprint_id, st.status = None, "backlog"
            moved += 1
    log_activity(f"Sprint completed: {sprint.name} ({done}/{total} points)", "sprint", sprint.id)
    notify("sprint_change", f"Sprint '{sprint.name}' completed: {done}/{total} points delivered", "sprint", sprint.id)
    db.session.commit()
    return ok({**sprint.to_dict(), "stories_returned_to_backlog": moved})


@api.post("/sprints/<int:id_>/assign-stories")
def assign_stories(id_):
    sprint = db.session.get(Sprint, id_) or _404("Sprint", id_)
    if sprint.status == "completed":
        raise ApiError("Cannot change a completed sprint", 409)
    ids = (request.get_json(silent=True) or {}).get("story_ids")
    if not isinstance(ids, list) or not all(isinstance(i, int) for i in ids):
        raise ApiError("story_ids must be a list of integers", 422)
    stories = UserStory.query.filter(UserStory.id.in_(ids)).all()
    if len(stories) != len(set(ids)):
        raise ApiError("One or more stories do not exist", 404)
    for st in stories:
        st.sprint_id = sprint.id
        if st.status == "backlog" and sprint.status == "active":
            st.status = "in_sprint"
    log_activity(f"{len(stories)} stories assigned to {sprint.name}", "sprint", sprint.id)
    db.session.flush()
    record_snapshot(sprint.id)
    db.session.commit()
    return ok(sprint.to_dict())


# ---------------------------------------------------------------- stories
STORY_SPEC = {"title": S(required=True, max=200), "description": S(), "acceptance_criteria": S(), "priority": S(choices=PRIORITIES),
              "story_points": {"type": "int", "min": 0, "max": 1000, "required": True}, "status": S(choices=STORY_STATUS),
              "mission_id": FK(), "sprint_id": FK()}


def story_before(obj, old):
    # column defaults are only applied at flush time, so treat missing values explicitly
    obj.status = obj.status or "backlog"
    if obj.rank in (None, 0) and old is None:
        obj.rank = (db.session.query(func.max(UserStory.rank)).scalar() or 0) + 1
    if obj.sprint_id is not None and (old is None or old.get("sprint_id") != obj.sprint_id):
        s = db.session.get(Sprint, obj.sprint_id)
        if s and s.status == "completed":
            raise ApiError("Cannot assign a story to a completed sprint", 409)
    if obj.sprint_id is None and obj.status == "in_sprint":
        obj.status = "backlog"
    if obj.sprint_id is not None and obj.status == "backlog":
        s = db.session.get(Sprint, obj.sprint_id)
        if s and s.status == "active":
            obj.status = "in_sprint"


def story_after(obj, old, created):
    db.session.flush()
    for sid in {obj.sprint_id, old.get("sprint_id")}:
        record_snapshot(sid)
    log_activity(f"Story {'created' if created else 'updated'}: {obj.title}", "story", obj.id)


register_crud(api, "stories", UserStory, STORY_SPEC, filters=("status", "priority", "mission_id", "sprint_id"),
              search=("title", "description"), order=[UserStory.rank, UserStory.id], label="Story",
              fk_models={"mission_id": Mission, "sprint_id": Sprint}, before_save=story_before, after_save=story_after,
              after_delete=lambda o, i: (db.session.flush(), record_snapshot(i.get("sprint_id"))))


@api.post("/stories/reorder")
def reorder_stories():
    ids = (request.get_json(silent=True) or {}).get("ids")
    if not isinstance(ids, list) or not all(isinstance(i, int) for i in ids):
        raise ApiError("ids must be a list of story ids in desired order", 422)
    by_id = {s.id: s for s in UserStory.query.filter(UserStory.id.in_(ids))}
    if len(by_id) != len(set(ids)):
        raise ApiError("One or more stories do not exist", 404)
    for i, sid in enumerate(ids, 1):
        by_id[sid].rank = i
    db.session.commit()
    return ok({"reordered": len(ids)})


# ---------------------------------------------------------------- tasks
TASK_SPEC = {"title": S(required=True, max=200), "description": S(), "status": S(choices=TASK_STATUS), "priority": S(choices=PRIORITIES),
             "assignee": S(max=120), "due_date": {"type": "date"}, "mission_id": FK(), "story_id": FK(), "sprint_id": FK()}


def task_before(obj, old):
    """On creation, a task linked to a story inherits the story's sprint and mission unless set explicitly."""
    if old is None and obj.story_id:
        story = db.session.get(UserStory, obj.story_id)
        if story:
            obj.sprint_id = obj.sprint_id or story.sprint_id
            obj.mission_id = obj.mission_id or story.mission_id


def task_save(obj, old, created):
    on_task_saved(obj, old.get("status"), old.get("assignee"), created)
    if not created and old.get("sprint_id") != obj.sprint_id:
        db.session.flush()
        record_snapshot(old.get("sprint_id"))


def task_after_delete(obj, info):
    db.session.flush()
    sync = obj.story_id
    from .services import sync_story_with_tasks
    sync_story_with_tasks(sync)
    db.session.flush()
    record_snapshot(info.get("sprint_id"))
    log_activity(f"Task deleted: {info['title']}", "task")


register_crud(api, "tasks", Task, TASK_SPEC, filters=("status", "priority", "mission_id", "story_id", "sprint_id", "assignee"),
              search=("title", "description"), label="Task",
              fk_models={"mission_id": Mission, "story_id": UserStory, "sprint_id": Sprint},
              before_save=task_before, after_save=task_save, after_delete=task_after_delete)

# ---------------------------------------------------------------- blockers
BLOCKER_SPEC = {"title": S(required=True, max=200), "description": S(), "severity": S(choices=PRIORITIES), "status": S(choices=BLOCKER_STATUS),
                "reported_date": {"type": "date"}, "task_id": FK()}


def blocker_before(obj, old):
    if obj.reported_date is None:
        obj.reported_date = date.today()
    if obj.status == "resolved" and not obj.resolved_at:
        obj.resolved_at = datetime.now(timezone.utc)
    elif obj.status != "resolved":
        obj.resolved_at = None


def blocker_after(obj, old, created):
    if created:
        notify("blocker", f"New {obj.severity} blocker: {obj.title}", "blocker", obj.id)
        log_activity(f"Blocker reported: {obj.title}", "blocker", obj.id)
    elif old.get("status") != obj.status:
        log_activity(f"Blocker '{obj.title}' is now {obj.status}", "blocker", obj.id)


register_crud(api, "blockers", Blocker, BLOCKER_SPEC, filters=("status", "severity", "task_id"), search=("title", "description"),
              label="Blocker", fk_models={"task_id": Task}, before_save=blocker_before, after_save=blocker_after)

# ---------------------------------------------------------------- retrospectives
RETRO_SPEC = {"sprint_id": FK(required=True), "went_well": S(), "needs_improvement": S()}


def retro_before(obj, old):
    if old is None and Retrospective.query.filter_by(sprint_id=obj.sprint_id).first():
        raise ApiError("A retrospective already exists for this sprint", 409)


register_crud(api, "retrospectives", Retrospective, RETRO_SPEC, filters=("sprint_id",), label="Retrospective",
              order=[Retrospective.created_at.desc()], fk_models={"sprint_id": Sprint}, before_save=retro_before,
              after_save=lambda o, old, c: log_activity(f"Retrospective {'added' if c else 'updated'} for sprint {o.sprint.name}", "retrospective", o.id))

ACTION_SPEC = {"retrospective_id": FK(required=True), "description": S(required=True, max=500), "owner": S(max=120), "status": S(choices=ACTION_STATUS)}
register_crud(api, "action-items", ActionItem, ACTION_SPEC, filters=("retrospective_id", "status"), label="Action item",
              fk_models={"retrospective_id": Retrospective})

# ---------------------------------------------------------------- notifications
@api.get("/notifications")
def list_notifications():
    check_due_dates()
    q = Notification.query
    if request.args.get("is_read") in ("true", "false"):
        q = q.filter_by(is_read=request.args["is_read"] == "true")
    items = q.order_by(Notification.created_at.desc(), Notification.id.desc()).limit(200).all()
    unread = Notification.query.filter_by(is_read=False).count()
    return ok([n.to_dict() for n in items], unread_count=unread)


@api.patch("/notifications/<int:id_>")
@api.put("/notifications/<int:id_>")
def update_notification(id_):
    n = db.session.get(Notification, id_) or _404("Notification", id_)
    body = request.get_json(silent=True) or {}
    if not isinstance(body.get("is_read"), bool):
        raise ApiError("Validation failed", 422, {"is_read": "must be true or false"})
    n.is_read = body["is_read"]
    db.session.commit()
    return ok(n.to_dict())


@api.post("/notifications/mark-all-read")
def mark_all_read():
    count = Notification.query.filter_by(is_read=False).update({"is_read": True})
    db.session.commit()
    return ok({"updated": count})


@api.delete("/notifications/<int:id_>")
def delete_notification(id_):
    n = db.session.get(Notification, id_) or _404("Notification", id_)
    db.session.delete(n)
    db.session.commit()
    return ok({"id": id_, "deleted": True})


def _404(label, id_):
    raise ApiError(f"{label} {id_} not found", 404)


from . import analytics  # noqa: E402,F401  (registers dashboard/analytics/report routes on `api`)

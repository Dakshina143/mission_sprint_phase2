"""Dashboard, analytics and reports. All values are computed from database records."""
import csv
import io
from datetime import date, timedelta

from flask import Response, request
from sqlalchemy import func

from .errors import ApiError, ok
from .extensions import db
from .models import Activity, Blocker, Mission, ProgressSnapshot, Retrospective, Sprint, Task, UserStory
from .routes import api

DEMO_PREFIX = "[DEMO]"


def pick_sprint():
    sid = request.args.get("sprint_id")
    if sid:
        s = db.session.get(Sprint, int(sid)) if sid.isdigit() else None
        if not s:
            raise ApiError(f"Sprint {sid} not found", 404)
        return s
    return (Sprint.query.filter_by(status="active").first()
            or Sprint.query.filter_by(status="completed").order_by(Sprint.completed_at.desc()).first())


def burndown_for(sprint):
    snaps = ProgressSnapshot.query.filter_by(sprint_id=sprint.id).order_by(ProgressSnapshot.snapshot_date).all()
    days = [sprint.start_date + timedelta(days=i) for i in range((sprint.end_date - sprint.start_date).days + 1)]
    start_total = snaps[0].total_points if snaps else sprint.points()[0]
    n = max(len(days) - 1, 1)
    ideal = [round(start_total * (1 - i / n), 2) for i in range(len(days))]
    limit = sprint.completed_at.date() if sprint.completed_at else date.today()
    actual, last, idx = [], None, 0
    for d in days:
        while idx < len(snaps) and snaps[idx].snapshot_date <= d:
            last = snaps[idx]
            idx += 1
        actual.append(last.remaining_points if last and d <= limit else None)
    return {"sprint": sprint.to_dict(), "labels": [d.isoformat() for d in days], "ideal": ideal, "actual": actual,
            "measured_days": len(snaps),
            "note": ("Actual line uses recorded measurements only; days without a new measurement carry the last recorded value, "
                     "and days before the first measurement are left blank. The ideal line is a calculated reference, not a measurement.")}


@api.get("/analytics/burndown")
def burndown():
    sprint = pick_sprint()
    if not sprint:
        return ok(None, message="No active or completed sprint yet.")
    return ok(burndown_for(sprint))


@api.get("/analytics/velocity")
def velocity():
    sprints = Sprint.query.filter_by(status="completed").order_by(Sprint.completed_at).all()
    rows = [{"sprint_id": s.id, "name": s.name, "committed": s.committed_points or 0, "delivered": s.delivered_points or 0} for s in sprints]
    avg = round(sum(r["delivered"] for r in rows) / len(rows), 1) if rows else None
    return ok({"sprints": rows, "average_velocity": avg})


@api.get("/analytics/sprint-completion")
def sprint_completion():
    out = []
    for s in Sprint.query.order_by(Sprint.start_date).all():
        total, done = s.points()
        tasks = s.tasks.count()
        tdone = s.tasks.filter_by(status="done").count()
        out.append({"sprint_id": s.id, "name": s.name, "status": s.status, "total_points": total, "completed_points": done,
                    "points_pct": round(100 * done / total, 1) if total else 0, "tasks_total": tasks, "tasks_done": tdone,
                    "tasks_pct": round(100 * tdone / tasks, 1) if tasks else 0})
    return ok(out)


@api.get("/analytics/mission-progress")
def mission_progress():
    return ok([{"mission_id": m.id, "title": m.title, "status": m.status, "progress": m.progress, "task_count": m.tasks.count()}
               for m in Mission.query.order_by(Mission.title).all()])


@api.get("/dashboard")
def dashboard():
    statuses = dict(db.session.query(Task.status, func.count(Task.id)).group_by(Task.status).all())
    dist = {k: statuses.get(k, 0) for k in ("todo", "in_progress", "in_review", "done")}
    sprint = Sprint.query.filter_by(status="active").first()
    current = None
    if sprint:
        total, done = sprint.points()
        tt, td = sprint.tasks.count(), sprint.tasks.filter_by(status="done").count()
        current = {**sprint.to_dict(), "tasks_total": tt, "tasks_done": td,
                   "progress_pct": round(100 * done / total, 1) if total else (round(100 * td / tt, 1) if tt else 0),
                   "days_remaining": max((sprint.end_date - date.today()).days, 0)}
    open_blockers = Blocker.query.filter(Blocker.status != "resolved")
    demo = any(db.session.query(m.id).filter(getattr(m, "title", getattr(m, "name", None)).like(f"{DEMO_PREFIX}%")).first()
               for m in (Mission, Sprint, UserStory, Task))
    return ok({
        "totals": {"missions": Mission.query.count(), "active_missions": Mission.query.filter_by(status="active").count(),
                   "tasks": sum(dist.values()), "completed_tasks": dist["done"]},
        "current_sprint": current,
        "backlog_stories": UserStory.query.filter_by(status="backlog").count(),
        "open_blockers": open_blockers.count(),
        "open_blocker_list": [b.to_dict() for b in open_blockers.order_by(Blocker.id.desc()).limit(5)],
        "task_status_distribution": dist,
        "recent_activity": [a.to_dict() for a in Activity.query.order_by(Activity.created_at.desc(), Activity.id.desc()).limit(10)],
        "demo_data_present": demo,
    })


# ---------------------------------------------------------------- reports
def _safe(v):
    if v is None:
        return ""
    s = str(v)
    return "'" + s if s[:1] in ("=", "+", "-", "@") else s  # neutralise spreadsheet formula injection


def report_rows(kind):
    if kind == "missions":
        h = ["id", "title", "priority", "status", "start_date", "end_date", "task_count", "progress_pct"]
        return h, [[m.id, m.title, m.priority, m.status, m.start_date, m.end_date, m.tasks.count(), m.progress] for m in Mission.query.order_by(Mission.id)]
    if kind == "tasks":
        h = ["id", "title", "status", "priority", "assignee", "due_date", "mission", "story", "sprint", "completed_at"]
        return h, [[t.id, t.title, t.status, t.priority, t.assignee, t.due_date, t.mission.title if t.mission else "",
                    t.story.title if t.story else "", t.sprint.name if t.sprint else "", t.completed_at] for t in Task.query.order_by(Task.id)]
    if kind == "sprints":
        h = ["id", "name", "status", "start_date", "end_date", "committed_points", "completed_points", "points_pct", "goal"]
        rows = []
        for s in Sprint.query.order_by(Sprint.start_date):
            t, d = s.points()
            rows.append([s.id, s.name, s.status, s.start_date, s.end_date, t, d, round(100 * d / t, 1) if t else 0, s.goal])
        return h, rows
    if kind == "blockers":
        h = ["id", "title", "severity", "status", "reported_date", "resolved_at", "task"]
        return h, [[b.id, b.title, b.severity, b.status, b.reported_date, b.resolved_at, b.task.title if b.task else ""] for b in Blocker.query.order_by(Blocker.id)]
    if kind == "retrospectives":
        h = ["id", "sprint", "went_well", "needs_improvement", "action_items"]
        return h, [[r.id, r.sprint.name, r.went_well, r.needs_improvement,
                    "; ".join(f"{a.description} [{a.status}{', ' + a.owner if a.owner else ''}]" for a in r.action_items)]
                   for r in Retrospective.query.order_by(Retrospective.id)]
    raise ApiError("Unknown report. Use missions, tasks, sprints, blockers or retrospectives.", 404)


@api.get("/reports/<kind>")
def report(kind):
    headers, rows = report_rows(kind)
    if request.args.get("format") == "csv":
        buf = io.StringIO()
        w = csv.writer(buf)
        w.writerow(headers)
        w.writerows([[_safe(c) for c in r] for r in rows])
        return Response(buf.getvalue(), mimetype="text/csv",
                        headers={"Content-Disposition": f"attachment; filename={kind}_report_{date.today()}.csv"})
    return ok({"report": kind, "generated_on": date.today().isoformat(), "columns": headers,
               "rows": [[None if c is None else (c if isinstance(c, (int, float)) else str(c)) for c in r] for r in rows]},
              count=len(rows))

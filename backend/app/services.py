"""Business logic: activity log, notifications, progress snapshots."""
from datetime import date, datetime, timedelta, timezone

from .extensions import db
from .models import Activity, Notification, ProgressSnapshot, Sprint, Task, UserStory


def log_activity(message, entity=None, entity_id=None):
    db.session.add(Activity(message=message, entity=entity, entity_id=entity_id))


def notify(type_, message, ref_type=None, ref_id=None, dedupe_key=None):
    if dedupe_key and Notification.query.filter_by(dedupe_key=dedupe_key).first():
        return
    db.session.add(Notification(type=type_, message=message, ref_type=ref_type, ref_id=ref_id, dedupe_key=dedupe_key))


def record_snapshot(sprint_id):
    """Upsert today's real progress measurement for a sprint (called whenever work changes)."""
    if not sprint_id:
        return
    sprint = db.session.get(Sprint, sprint_id)
    if not sprint or sprint.status == "planned":
        return
    db.session.flush()
    total, done = sprint.points()
    today = date.today()
    snap = ProgressSnapshot.query.filter_by(sprint_id=sprint_id, snapshot_date=today).first()
    if not snap:
        snap = ProgressSnapshot(sprint_id=sprint_id, snapshot_date=today)
        db.session.add(snap)
    snap.total_points, snap.completed_points, snap.remaining_points = total, done, total - done


def sync_story_with_tasks(story_id):
    """A story with tasks is done when all of its tasks are done; otherwise it returns to in_sprint/backlog."""
    story = db.session.get(UserStory, story_id) if story_id else None
    if not story:
        return
    tasks = story.tasks.all()
    if not tasks:
        return
    all_done = all(t.status == "done" for t in tasks)
    if all_done and story.status != "done":
        story.status = "done"
    elif not all_done and story.status == "done":
        story.status = "in_sprint" if story.sprint_id else "backlog"


def on_task_saved(task, old_status=None, old_assignee=None, created=False):
    if task.status == "done" and not task.completed_at:
        task.completed_at = datetime.now(timezone.utc)
    elif task.status != "done":
        task.completed_at = None
    if task.assignee and (created or task.assignee != old_assignee):
        db.session.flush()
        notify("task_assigned", f"Task '{task.title}' assigned to {task.assignee}", "task", task.id)
    if created:
        log_activity(f"Task created: {task.title}", "task", task.id)
    elif old_status and old_status != task.status:
        log_activity(f"Task '{task.title}' moved {old_status} → {task.status}", "task", task.id)
    sync_story_with_tasks(task.story_id)
    db.session.flush()
    record_snapshot(task.sprint_id)


def check_due_dates():
    """Create (deduplicated) notifications for open tasks that are overdue or due within 2 days."""
    today = date.today()
    soon = today + timedelta(days=2)
    for t in Task.query.filter(Task.status != "done", Task.due_date.isnot(None), Task.due_date <= soon):
        overdue = t.due_date < today
        msg = f"Task '{t.title}' is overdue (was due {t.due_date})" if overdue else f"Task '{t.title}' is due {t.due_date}"
        notify("due_date", msg, "task", t.id, dedupe_key=f"due:{t.id}:{t.due_date}:{'o' if overdue else 's'}")
    db.session.commit()

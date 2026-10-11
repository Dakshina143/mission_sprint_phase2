"""Optional demo data. Every record is prefixed [DEMO]. No historical measurements are fabricated:
the only progress snapshot is the real, current state of the active sprint, taken at seeding time."""
from datetime import date, timedelta

from .extensions import db
from .models import (ActionItem, Blocker, Mission, Notification, ProgressSnapshot, Retrospective, Sprint, Task, UserStory)
from .services import log_activity, on_task_saved, record_snapshot

P = "[DEMO] "


def seed(reset=False):
    if reset:
        for M in (ProgressSnapshot, Notification, ActionItem, Retrospective, Blocker, Task, UserStory, Sprint, Mission):
            M.query.delete()
        db.session.commit()
    elif Mission.query.filter(Mission.title.like(P + "%")).first():
        return "Demo data already present (use --reset to rebuild)."
    t = date.today()
    m1 = Mission(title=P + "Customer portal launch", description="Ship the self-service portal.", priority="high", status="active", start_date=t - timedelta(days=30), end_date=t + timedelta(days=45))
    m2 = Mission(title=P + "Payments reliability", description="Reduce failed payment retries.", priority="critical", status="active", start_date=t - timedelta(days=10), end_date=t + timedelta(days=60))
    m3 = Mission(title=P + "Internal tooling cleanup", priority="low", status="planning")
    db.session.add_all([m1, m2, m3])
    done_sprint = Sprint(name=P + "Sprint 1", goal="Foundations", start_date=t - timedelta(days=28), end_date=t - timedelta(days=15), status="completed")
    active = Sprint(name=P + "Sprint 2", goal="Login and account settings", start_date=t - timedelta(days=3), end_date=t + timedelta(days=10), status="planned")
    nxt = Sprint(name=P + "Sprint 3", goal="Payments retry policy", start_date=t + timedelta(days=11), end_date=t + timedelta(days=24))
    db.session.add_all([done_sprint, active, nxt])
    db.session.flush()
    # completed sprint history (clearly demo; derived from stories/tasks created below, not invented series)
    s1 = UserStory(title=P + "Set up project skeleton", story_points=3, status="done", priority="high", mission_id=m1.id, sprint_id=done_sprint.id, rank=1)
    s2 = UserStory(title=P + "User login", description="Users sign in with email.", acceptance_criteria="- Valid login works\n- Invalid shows an error", story_points=5, priority="high", status="in_sprint", mission_id=m1.id, sprint_id=active.id, rank=2)
    s3 = UserStory(title=P + "Account settings page", story_points=3, priority="medium", status="in_sprint", mission_id=m1.id, sprint_id=active.id, rank=3)
    s4 = UserStory(title=P + "Retry policy for failed charges", story_points=8, priority="critical", mission_id=m2.id, rank=4)
    s5 = UserStory(title=P + "Payment failure dashboard", story_points=5, priority="medium", mission_id=m2.id, rank=5)
    db.session.add_all([s1, s2, s3, s4, s5])
    db.session.flush()
    done_sprint.committed_points, done_sprint.delivered_points = 3, 3
    active_tasks = [
        Task(title=P + "Design login form", status="done", priority="high", assignee="Asha", mission_id=m1.id, story_id=s2.id, sprint_id=active.id),
        Task(title=P + "Implement login endpoint", status="in_progress", priority="high", assignee="Ravi", due_date=t + timedelta(days=1), mission_id=m1.id, story_id=s2.id, sprint_id=active.id),
        Task(title=P + "Settings page layout", status="in_review", assignee="Asha", mission_id=m1.id, story_id=s3.id, sprint_id=active.id),
        Task(title=P + "Write retry policy ADR", status="todo", priority="medium", mission_id=m2.id, story_id=s4.id),
    ]
    db.session.add_all(active_tasks)
    db.session.add(Task(title=P + "Scaffold repo", status="done", mission_id=m1.id, story_id=s1.id, sprint_id=done_sprint.id))
    db.session.flush()
    # start the active sprint through the same logic as the API
    active.status, active.started_at = "active", db.func.now()
    db.session.flush()
    for tk in active_tasks:
        on_task_saved(tk, created=True)
    record_snapshot(active.id)
    b = Blocker(title=P + "Staging database access", description="Waiting on credentials for staging.", severity="high", status="open", task_id=active_tasks[1].id)
    db.session.add(b)
    r = Retrospective(sprint_id=done_sprint.id, went_well="Clear scope, quick setup.", needs_improvement="Estimates were rough.")
    r.action_items = [ActionItem(description="Hold a short estimation session before planning", owner="Team", status="open")]
    db.session.add(r)
    log_activity("Demo data loaded", "system")
    db.session.commit()
    return "Demo data loaded. All demo records are prefixed [DEMO]."

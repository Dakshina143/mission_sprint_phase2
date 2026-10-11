"""CRUD and workflow tests for missions, stories, sprints, tasks, blockers and retrospectives."""
from datetime import date, timedelta

from conftest import mk

D = lambda n: (date.today() + timedelta(days=n)).isoformat()
j = lambda r: r.get_json()


# ------------------------------------------------------------------ missions
def test_mission_full_crud_cycle(client):
    m = mk(client, "missions", title="Portal", description="d", priority="high", status="active", start_date=D(0), end_date=D(30))
    assert m["progress"] == 0 and m["task_count"] == 0
    got = j(client.get(f"/api/missions/{m['id']}"))["data"]
    assert got["title"] == "Portal" and got["start_date"] == D(0)
    r = client.put(f"/api/missions/{m['id']}", json={"title": "Portal v2", "status": "on_hold"})
    assert r.status_code == 200 and j(r)["data"]["status"] == "on_hold"
    assert j(client.get("/api/missions"))["data"][0]["title"] == "Portal v2"
    assert client.delete(f"/api/missions/{m['id']}").status_code == 200
    assert client.get("/api/missions").get_json()["data"] == []


def test_deleting_mission_keeps_tasks_but_unlinks_them(client):
    m = mk(client, "missions", title="M")
    t = mk(client, "tasks", title="T", mission_id=m["id"])
    client.delete(f"/api/missions/{m['id']}")
    assert j(client.get(f"/api/tasks/{t['id']}"))["data"]["mission_id"] is None


# ------------------------------------------------------------------ stories
def test_story_crud_and_filters(client):
    m = mk(client, "missions", title="M")
    s = mk(client, "stories", title="Login", description="d", acceptance_criteria="works", story_points=5, priority="high", mission_id=m["id"])
    assert s["status"] == "backlog" and s["rank"] >= 1
    mk(client, "stories", title="Other", story_points=1, priority="low")
    assert len(j(client.get(f"/api/stories?mission_id={m['id']}"))["data"]) == 1
    assert len(j(client.get("/api/stories?priority=low"))["data"]) == 1
    assert len(j(client.get("/api/stories?q=login"))["data"]) == 1
    r = client.patch(f"/api/stories/{s['id']}", json={"story_points": 8, "acceptance_criteria": "updated"})
    assert j(r)["data"]["story_points"] == 8
    assert client.delete(f"/api/stories/{s['id']}").status_code == 200
    assert client.get(f"/api/stories/{s['id']}").status_code == 404


def test_story_validation(client):
    for body in ({"title": "x"}, {"title": "x", "story_points": -1}, {"title": "x", "story_points": 1.5},
                 {"title": "x", "story_points": 5000}, {"title": "x", "story_points": 1, "priority": "urgent"},
                 {"story_points": 1}, {"title": "x", "story_points": 1, "sprint_id": 12345}):
        assert client.post("/api/stories", json=body).status_code == 422, body


def test_story_in_active_sprint_becomes_in_sprint_and_completed_sprint_is_closed(client):
    sp = mk(client, "sprints", name="S", start_date=D(0), end_date=D(3))
    client.post(f"/api/sprints/{sp['id']}/start")
    assert mk(client, "stories", title="a", story_points=2, sprint_id=sp["id"])["status"] == "in_sprint"
    client.post(f"/api/sprints/{sp['id']}/complete", json={})
    r = client.post("/api/stories", json={"title": "late", "story_points": 1, "sprint_id": sp["id"]})
    assert r.status_code == 409


# ------------------------------------------------------------------ sprints
def test_sprint_crud_and_validation(client):
    sp = mk(client, "sprints", name="S1", goal="g", start_date=D(0), end_date=D(7))
    assert sp["status"] == "planned" and sp["total_points"] == 0
    assert client.post("/api/sprints", json={"name": "bad", "start_date": D(5), "end_date": D(1)}).status_code == 422
    assert client.post("/api/sprints", json={"name": "bad"}).status_code == 422
    assert client.patch(f"/api/sprints/{sp['id']}", json={"end_date": D(-3)}).status_code == 422
    assert j(client.get(f"/api/sprints/{sp['id']}"))["data"]["end_date"] == D(7)  # rejected change was not saved
    assert j(client.patch(f"/api/sprints/{sp['id']}", json={"goal": "new"}))["data"]["goal"] == "new"
    assert len(j(client.get("/api/sprints?status=planned"))["data"]) == 1
    assert client.delete(f"/api/sprints/{sp['id']}").status_code == 200


def test_sprint_state_machine(client):
    sp = mk(client, "sprints", name="S", start_date=D(0), end_date=D(3))
    assert client.post(f"/api/sprints/{sp['id']}/complete", json={}).status_code == 409  # not active yet
    assert client.post(f"/api/sprints/{sp['id']}/start").status_code == 200
    assert client.post(f"/api/sprints/{sp['id']}/start").status_code == 409
    assert client.post(f"/api/sprints/{sp['id']}/complete", json={}).status_code == 200
    assert client.post(f"/api/sprints/{sp['id']}/assign-stories", json={"story_ids": []}).status_code == 409
    assert client.post("/api/sprints/9999/start").status_code == 404


def test_deleting_sprint_unlinks_stories_and_removes_retro(client):
    sp = mk(client, "sprints", name="S", start_date=D(0), end_date=D(3))
    st = mk(client, "stories", title="a", story_points=1, sprint_id=sp["id"])
    mk(client, "retrospectives", sprint_id=sp["id"])
    assert client.delete(f"/api/sprints/{sp['id']}").status_code == 200
    assert j(client.get(f"/api/stories/{st['id']}"))["data"]["sprint_id"] is None
    assert j(client.get("/api/retrospectives"))["data"] == []


# ------------------------------------------------------------------ tasks
def test_task_crud_and_status_changes(client):
    t = mk(client, "tasks", title="Build", priority="high", due_date=D(3))
    assert t["status"] == "todo" and t["completed_at"] is None
    for status in ("in_progress", "in_review"):
        assert j(client.patch(f"/api/tasks/{t['id']}", json={"status": status}))["data"]["status"] == status
    done = j(client.patch(f"/api/tasks/{t['id']}", json={"status": "done"}))["data"]
    assert done["completed_at"] is not None
    reopened = j(client.patch(f"/api/tasks/{t['id']}", json={"status": "todo"}))["data"]
    assert reopened["completed_at"] is None
    assert client.patch(f"/api/tasks/{t['id']}", json={"status": "finished"}).status_code == 422
    assert len(j(client.get("/api/tasks?status=todo"))["data"]) == 1
    assert client.delete(f"/api/tasks/{t['id']}").status_code == 200
    assert client.get(f"/api/tasks/{t['id']}").status_code == 404


def test_status_changes_are_recorded_in_activity(client):
    t = mk(client, "tasks", title="Build")
    client.patch(f"/api/tasks/{t['id']}", json={"status": "in_progress"})
    messages = [a["message"] for a in j(client.get("/api/dashboard"))["data"]["recent_activity"]]
    assert any("todo → in_progress" in m for m in messages)


def test_task_inherits_sprint_and_mission_from_story(client):
    m = mk(client, "missions", title="M")
    sp = mk(client, "sprints", name="S", start_date=D(0), end_date=D(3))
    st = mk(client, "stories", title="s", story_points=2, mission_id=m["id"], sprint_id=sp["id"])
    t = mk(client, "tasks", title="t", story_id=st["id"])
    assert t["sprint_id"] == sp["id"] and t["mission_id"] == m["id"]


def test_assignment_notification_only_when_assignee_changes(client):
    t = mk(client, "tasks", title="T", assignee="Asha")
    client.patch(f"/api/tasks/{t['id']}", json={"assignee": "Asha", "priority": "high"})
    assert len([n for n in j(client.get("/api/notifications"))["data"] if n["type"] == "task_assigned"]) == 1
    client.patch(f"/api/tasks/{t['id']}", json={"assignee": "Ravi"})
    msgs = [n["message"] for n in j(client.get("/api/notifications"))["data"] if n["type"] == "task_assigned"]
    assert len(msgs) == 2 and any("Ravi" in m for m in msgs)


def test_deleting_task_updates_story_and_blocker_link(client):
    st = mk(client, "stories", title="s", story_points=1)
    t1 = mk(client, "tasks", title="a", story_id=st["id"])
    t2 = mk(client, "tasks", title="b", story_id=st["id"], status="done")
    b = mk(client, "blockers", title="blk", task_id=t1["id"])
    client.delete(f"/api/tasks/{t1['id']}")
    assert j(client.get(f"/api/stories/{st['id']}"))["data"]["status"] == "done"  # only remaining task is done
    assert j(client.get(f"/api/blockers/{b['id']}"))["data"]["task_id"] is None
    assert t2["id"]


# ------------------------------------------------------------------ blockers
def test_blocker_workflow(client):
    t = mk(client, "tasks", title="T")
    b = mk(client, "blockers", title="No access", description="d", severity="high", task_id=t["id"], reported_date=D(-1))
    assert b["status"] == "open" and b["reported_date"] == D(-1) and b["resolved_at"] is None
    assert j(client.patch(f"/api/blockers/{b['id']}", json={"status": "in_progress"}))["data"]["status"] == "in_progress"
    assert j(client.get("/api/dashboard"))["data"]["open_blockers"] == 1
    r = j(client.patch(f"/api/blockers/{b['id']}", json={"status": "resolved"}))["data"]
    assert r["resolved_at"] is not None
    assert j(client.get("/api/dashboard"))["data"]["open_blockers"] == 0
    assert j(client.patch(f"/api/blockers/{b['id']}", json={"status": "open"}))["data"]["resolved_at"] is None
    assert len(j(client.get("/api/blockers?severity=high"))["data"]) == 1
    assert len(j(client.get(f"/api/blockers?task_id={t['id']}"))["data"]) == 1
    assert client.delete(f"/api/blockers/{b['id']}").status_code == 200


def test_blocker_validation(client):
    assert client.post("/api/blockers", json={"title": "x", "severity": "huge"}).status_code == 422
    assert client.post("/api/blockers", json={"title": "x", "task_id": 999}).status_code == 422
    assert client.post("/api/blockers", json={"title": "x", "reported_date": "yesterday"}).status_code == 422


# ------------------------------------------------------------------ retrospectives
def test_retrospective_workflow(client):
    sp = mk(client, "sprints", name="S1", start_date=D(-7), end_date=D(-1))
    r = mk(client, "retrospectives", sprint_id=sp["id"], went_well="a", needs_improvement="b")
    assert j(client.patch(f"/api/retrospectives/{r['id']}", json={"went_well": "a2"}))["data"]["went_well"] == "a2"
    ai = mk(client, "action-items", retrospective_id=r["id"], description="Pair more", owner="Sam")
    assert j(client.patch(f"/api/action-items/{ai['id']}", json={"status": "done"}))["data"]["status"] == "done"
    assert client.patch(f"/api/action-items/{ai['id']}", json={"status": "later"}).status_code == 422
    assert client.post("/api/action-items", json={"retrospective_id": 999, "description": "x"}).status_code == 422
    got = j(client.get(f"/api/retrospectives/{r['id']}"))["data"]
    assert got["action_items"][0]["status"] == "done"
    assert len(j(client.get(f"/api/retrospectives?sprint_id={sp['id']}"))["data"]) == 1
    client.delete(f"/api/retrospectives/{r['id']}")
    assert client.get(f"/api/action-items/{ai['id']}").status_code == 404  # cascade
    assert client.post("/api/retrospectives", json={"sprint_id": 999}).status_code == 422

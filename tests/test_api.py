from datetime import date, timedelta

from conftest import mk

D = lambda n: (date.today() + timedelta(days=n)).isoformat()


def test_health_checks_database(client):
    r = client.get("/api/health")
    assert r.status_code == 200 and r.get_json()["data"]["database"] == "connected"


def test_health_reports_failure_when_db_down(client, app, monkeypatch):
    from app.extensions import db
    monkeypatch.setattr(db.session, "execute", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("down")))
    r = client.get("/api/health")
    assert r.status_code == 503 and r.get_json()["data"]["database"] == "unreachable"


def test_mission_crud_validation_search_filter(client):
    r = client.post("/api/missions", json={"title": ""})
    assert r.status_code == 422 and "title" in r.get_json()["error"]["details"]
    assert client.post("/api/missions", json={"title": "x", "priority": "urgent"}).status_code == 422
    assert client.post("/api/missions", json={"title": "x", "start_date": D(5), "end_date": D(1)}).status_code == 422
    m = mk(client, "missions", title="Alpha launch", priority="high", status="active")
    mk(client, "missions", title="Beta", priority="low")
    assert len(client.get("/api/missions?q=alpha").get_json()["data"]) == 1
    assert len(client.get("/api/missions?status=active").get_json()["data"]) == 1
    r = client.put(f"/api/missions/{m['id']}", json={"title": "Alpha 2"})
    assert r.get_json()["data"]["title"] == "Alpha 2"
    assert client.delete(f"/api/missions/{m['id']}").status_code == 200
    r = client.get(f"/api/missions/{m['id']}")
    assert r.status_code == 404 and r.get_json()["success"] is False


def test_mission_progress_from_tasks(client):
    m = mk(client, "missions", title="M")
    t1 = mk(client, "tasks", title="a", mission_id=m["id"])
    mk(client, "tasks", title="b", mission_id=m["id"])
    assert client.get(f"/api/missions/{m['id']}").get_json()["data"]["progress"] == 0
    client.patch(f"/api/tasks/{t1['id']}", json={"status": "done"})
    assert client.get(f"/api/missions/{m['id']}").get_json()["data"]["progress"] == 50.0


def test_invalid_foreign_key_and_json(client):
    r = client.post("/api/tasks", json={"title": "t", "mission_id": 999})
    assert r.status_code == 422
    assert client.post("/api/tasks", data="not json", content_type="application/json").status_code == 400


def test_sprint_lifecycle_and_velocity(client):
    sp = mk(client, "sprints", name="S1", start_date=D(0), end_date=D(7))
    sp2 = mk(client, "sprints", name="S2", start_date=D(8), end_date=D(14))
    a = mk(client, "stories", title="A", story_points=5)
    b = mk(client, "stories", title="B", story_points=3)
    assert client.post(f"/api/sprints/{sp['id']}/assign-stories", json={"story_ids": [a["id"], b["id"]]}).status_code == 200
    started = client.post(f"/api/sprints/{sp['id']}/start").get_json()["data"]
    assert started["status"] == "active" and started["total_points"] == 8
    assert client.post(f"/api/sprints/{sp2['id']}/start").status_code == 409  # only one active sprint
    client.patch(f"/api/stories/{a['id']}", json={"status": "done"})
    done = client.post(f"/api/sprints/{sp['id']}/complete", json={}).get_json()["data"]
    assert done["status"] == "completed" and done["completed_points"] == 5 and done["total_points"] == 8
    assert done["stories_returned_to_backlog"] == 1
    # history preserved even though story B left the sprint
    again = client.get(f"/api/sprints/{sp['id']}").get_json()["data"]
    assert again["total_points"] == 8
    v = client.get("/api/analytics/velocity").get_json()["data"]
    assert v["sprints"][0]["delivered"] == 5 and v["average_velocity"] == 5.0
    assert client.get(f"/api/stories/{b['id']}").get_json()["data"]["status"] == "backlog"


def test_task_status_updates_story_and_burndown_snapshot(client):
    sp = mk(client, "sprints", name="S", start_date=D(-1), end_date=D(5))
    st = mk(client, "stories", title="Story", story_points=5, sprint_id=sp["id"])
    t = mk(client, "tasks", title="T", story_id=st["id"], sprint_id=sp["id"])
    assert client.get(f"/api/analytics/burndown?sprint_id={sp['id']}").get_json()["data"]["measured_days"] == 0
    client.post(f"/api/sprints/{sp['id']}/start")
    client.patch(f"/api/tasks/{t['id']}", json={"status": "done"})
    assert client.get(f"/api/stories/{st['id']}").get_json()["data"]["status"] == "done"
    bd = client.get(f"/api/analytics/burndown?sprint_id={sp['id']}").get_json()["data"]
    assert bd["measured_days"] == 1
    measured = [x for x in bd["actual"] if x is not None]
    assert measured == [0]  # real measurement only; no fabricated history before today
    assert bd["actual"][0] is None
    client.patch(f"/api/tasks/{t['id']}", json={"status": "in_review"})
    assert client.get(f"/api/stories/{st['id']}").get_json()["data"]["status"] == "in_sprint"


def test_burndown_without_sprint(client):
    r = client.get("/api/analytics/burndown").get_json()
    assert r["data"] is None


def test_story_reorder(client):
    a, b, c = (mk(client, "stories", title=x, story_points=1) for x in "abc")
    client.post("/api/stories/reorder", json={"ids": [c["id"], a["id"], b["id"]]})
    assert [s["title"] for s in client.get("/api/stories").get_json()["data"]] == ["c", "a", "b"]


def test_blockers_filter_and_resolution(client):
    t = mk(client, "tasks", title="T")
    b = mk(client, "blockers", title="DB down", severity="critical", task_id=t["id"])
    mk(client, "blockers", title="Other", status="resolved")
    assert len(client.get("/api/blockers?status=open").get_json()["data"]) == 1
    r = client.patch(f"/api/blockers/{b['id']}", json={"status": "resolved"}).get_json()["data"]
    assert r["resolved_at"] is not None
    assert client.get("/api/dashboard").get_json()["data"]["open_blockers"] == 0


def test_retrospective_and_action_items(client):
    sp = mk(client, "sprints", name="S", start_date=D(-7), end_date=D(-1))
    r = mk(client, "retrospectives", sprint_id=sp["id"], went_well="ok", needs_improvement="meh")
    assert client.post("/api/retrospectives", json={"sprint_id": sp["id"]}).status_code == 409
    mk(client, "action-items", retrospective_id=r["id"], description="Do thing", owner="Sam")
    got = client.get(f"/api/retrospectives/{r['id']}").get_json()["data"]
    assert got["action_items"][0]["status"] == "open" and got["sprint_name"] == "S"


def test_notifications(client):
    mk(client, "tasks", title="Assigned", assignee="Asha")
    mk(client, "tasks", title="Late", due_date=D(-1))
    mk(client, "blockers", title="B")
    sp = mk(client, "sprints", name="S", start_date=D(0), end_date=D(3))
    client.post(f"/api/sprints/{sp['id']}/start")
    body = client.get("/api/notifications").get_json()
    types = {n["type"] for n in body["data"]}
    assert {"task_assigned", "due_date", "blocker", "sprint_change"} <= types
    n_before = len(body["data"])
    assert len(client.get("/api/notifications").get_json()["data"]) == n_before  # due-date alerts are deduplicated
    nid = body["data"][0]["id"]
    assert client.patch(f"/api/notifications/{nid}", json={"is_read": True}).get_json()["data"]["is_read"] is True
    assert client.post("/api/notifications/mark-all-read").get_json()["data"]["updated"] == body["unread_count"] - 1
    assert client.get("/api/notifications?is_read=false").get_json()["data"] == []


def test_dashboard_counts(client):
    m = mk(client, "missions", title="M", status="active")
    mk(client, "tasks", title="a", mission_id=m["id"], status="done")
    mk(client, "tasks", title="b", mission_id=m["id"])
    d = client.get("/api/dashboard").get_json()["data"]
    assert d["totals"] == {"missions": 1, "active_missions": 1, "tasks": 2, "completed_tasks": 1}
    assert d["task_status_distribution"]["todo"] == 1 and d["demo_data_present"] is False


def test_reports_use_db_and_csv_is_safe(client):
    mk(client, "missions", title="=HYPERLINK(1)")
    r = client.get("/api/reports/missions?format=csv")
    assert r.mimetype == "text/csv" and "'=HYPERLINK" in r.get_data(as_text=True)
    assert client.get("/api/reports/missions").get_json()["count"] == 1
    assert client.get("/api/reports/nonsense").status_code == 404
    for kind in ("tasks", "sprints", "blockers", "retrospectives"):
        assert client.get(f"/api/reports/{kind}").status_code == 200


def test_cicd_integration_point_unconfigured(client):
    assert client.get("/api/integrations/cicd").get_json()["data"]["status"] == "not_configured"


def test_seed_is_labelled_and_idempotent(app, client):
    from app.seed import seed
    seed()
    assert "already present" in seed()
    assert client.get("/api/dashboard").get_json()["data"]["demo_data_present"] is True
    assert all(m["title"].startswith("[DEMO]") for m in client.get("/api/missions").get_json()["data"])

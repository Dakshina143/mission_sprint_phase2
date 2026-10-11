"""Analytics calculations, error handling, health and metrics."""
from datetime import date, timedelta

from app.extensions import db
from app.models import ProgressSnapshot
from conftest import mk

D = lambda n: (date.today() + timedelta(days=n)).isoformat()
j = lambda r: r.get_json()


def _snap(sprint_id, day, total, done):
    db.session.add(ProgressSnapshot(sprint_id=sprint_id, snapshot_date=date.today() + timedelta(days=day),
                                    total_points=total, completed_points=done, remaining_points=total - done))
    db.session.commit()


# ------------------------------------------------------------------ analytics
def test_burndown_ideal_line_and_measured_values(client, app):
    sp = mk(client, "sprints", name="S", start_date=D(-2), end_date=D(2))
    _snap(sp["id"], -2, 10, 0)
    _snap(sp["id"], 0, 10, 4)
    bd = j(client.get(f"/api/analytics/burndown?sprint_id={sp['id']}"))["data"]
    assert bd["ideal"] == [10, 7.5, 5, 2.5, 0]
    # measured: day -2 = 10, carried to day -1 = 10, today = 6, future days stay blank (no fabricated data)
    assert bd["actual"] == [10, 10, 6, None, None]
    assert bd["measured_days"] == 2 and len(bd["labels"]) == 5


def test_burndown_has_no_actual_values_without_measurements(client):
    sp = mk(client, "sprints", name="S", start_date=D(-2), end_date=D(2))
    bd = j(client.get(f"/api/analytics/burndown?sprint_id={sp['id']}"))["data"]
    assert all(v is None for v in bd["actual"]) and bd["measured_days"] == 0
    assert client.get("/api/analytics/burndown?sprint_id=9999").status_code == 404


def test_velocity_average_from_completed_sprints(client):
    for name, pts in (("A", 5), ("B", 8)):
        sp = mk(client, "sprints", name=name, start_date=D(0), end_date=D(5))
        st = mk(client, "stories", title=f"s{name}", story_points=pts, sprint_id=sp["id"])
        client.post(f"/api/sprints/{sp['id']}/start")
        client.patch(f"/api/stories/{st['id']}", json={"status": "done"})
        client.post(f"/api/sprints/{sp['id']}/complete", json={})
    v = j(client.get("/api/analytics/velocity"))["data"]
    assert [s["delivered"] for s in v["sprints"]] == [5, 8] and v["average_velocity"] == 6.5


def test_velocity_empty_when_no_completed_sprints(client):
    assert j(client.get("/api/analytics/velocity"))["data"] == {"sprints": [], "average_velocity": None}


def test_sprint_completion_and_mission_progress(client):
    m = mk(client, "missions", title="M")
    sp = mk(client, "sprints", name="S", start_date=D(0), end_date=D(5))
    done_story = mk(client, "stories", title="a", story_points=3, sprint_id=sp["id"])
    mk(client, "stories", title="b", story_points=1, sprint_id=sp["id"])
    client.patch(f"/api/stories/{done_story['id']}", json={"status": "done"})
    t1 = mk(client, "tasks", title="t1", sprint_id=sp["id"], mission_id=m["id"])
    mk(client, "tasks", title="t2", sprint_id=sp["id"], mission_id=m["id"])
    mk(client, "tasks", title="t3", sprint_id=sp["id"], mission_id=m["id"])
    client.patch(f"/api/tasks/{t1['id']}", json={"status": "done"})
    row = j(client.get("/api/analytics/sprint-completion"))["data"][0]
    assert (row["total_points"], row["completed_points"], row["points_pct"]) == (4, 3, 75.0)
    assert (row["tasks_total"], row["tasks_done"], row["tasks_pct"]) == (3, 1, 33.3)
    mp = j(client.get("/api/analytics/mission-progress"))["data"][0]
    assert mp["progress"] == 33.3 and mp["task_count"] == 3


def test_dashboard_current_sprint_and_distribution(client):
    sp = mk(client, "sprints", name="S", start_date=D(-1), end_date=D(4))
    mk(client, "stories", title="a", story_points=4, sprint_id=sp["id"])
    client.post(f"/api/sprints/{sp['id']}/start")
    mk(client, "tasks", title="x", sprint_id=sp["id"], status="done")
    mk(client, "tasks", title="y", sprint_id=sp["id"], status="in_review")
    d = j(client.get("/api/dashboard"))["data"]
    assert d["current_sprint"]["name"] == "S" and d["current_sprint"]["tasks_total"] == 2
    assert d["current_sprint"]["days_remaining"] == 4
    assert d["task_status_distribution"] == {"todo": 0, "in_progress": 0, "in_review": 1, "done": 1}
    assert d["backlog_stories"] == 0


def test_reports_reflect_database_rows(client):
    m = mk(client, "missions", title="M")
    mk(client, "tasks", title="T", mission_id=m["id"], status="done")
    body = j(client.get("/api/reports/tasks"))
    assert body["count"] == 1 and body["data"]["rows"][0][1] == "T"
    csv_text = client.get("/api/reports/missions?format=csv").get_data(as_text=True)
    assert csv_text.splitlines()[0].startswith("id,title") and "100.0" in csv_text


# ------------------------------------------------------------------ errors
def test_error_envelope_for_http_errors(client):
    r = client.get("/api/nope")
    assert r.status_code == 404 and j(r)["success"] is False and "message" in j(r)["error"]
    assert client.delete("/api/health").status_code == 405
    assert client.post("/api/tasks", data="{bad json", content_type="application/json").status_code == 400
    assert client.post("/api/tasks", json=[1, 2]).status_code == 400


def test_invalid_filter_values_are_422_not_500(client):
    assert client.get("/api/tasks?sprint_id=abc").status_code == 422
    assert client.get("/api/tasks?mission_id=99999999999999").status_code == 422
    assert client.get("/api/tasks?status=nonsense").status_code == 200  # unknown enum value just matches nothing


def test_validation_details_name_each_field(client):
    r = client.post("/api/tasks", json={"title": "", "priority": "x", "due_date": "2026-13-45", "mission_id": "nan"})
    assert r.status_code == 422
    assert set(j(r)["error"]["details"]) == {"title", "priority", "due_date", "mission_id"}


def test_failed_validation_does_not_leak_changes(client):
    sp = mk(client, "sprints", name="S", start_date=D(0), end_date=D(5))
    assert client.patch(f"/api/sprints/{sp['id']}", json={"end_date": D(-5)}).status_code == 422
    assert client.post("/api/missions", json={"title": "ok"}).status_code == 201  # no stale invalid state flushed
    assert client.get(f"/api/sprints/{sp['id']}").get_json()["data"]["end_date"] == D(5)


def test_unknown_fields_are_ignored_and_ids_not_settable(client):
    m = mk(client, "missions", title="M", id=999, progress=100, hacker="x")
    assert m["id"] != 999 and m["progress"] == 0


# ------------------------------------------------------------------ health and metrics
def test_liveness_does_not_touch_database(client, monkeypatch):
    monkeypatch.setattr(db.session, "execute", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("db down")))
    assert client.get("/api/health/live").status_code == 200
    assert client.get("/api/health").status_code == 503


def test_metrics_exposes_persisted_data(client):
    mk(client, "missions", title="M", status="active")
    t = mk(client, "tasks", title="T")
    client.patch(f"/api/tasks/{t['id']}", json={"status": "done"})
    mk(client, "blockers", title="B")
    client.get("/api/health")
    text = client.get("/metrics").get_data(as_text=True)
    assert "missionsprint_database_up 1.0" in text
    assert 'missionsprint_missions{status="active"} 1.0' in text
    assert 'missionsprint_tasks{status="done"} 1.0' in text
    assert 'missionsprint_blockers{status="open"} 1.0' in text
    assert 'missionsprint_http_requests_total{endpoint="/api/health",method="GET",status="200"} 1.0' in text


def test_metrics_report_database_down_without_inventing_zeroes(client, monkeypatch):
    monkeypatch.setattr(db.session, "execute", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("db down")))
    text = client.get("/metrics").get_data(as_text=True)
    assert "missionsprint_database_up 0.0" in text
    assert "missionsprint_tasks{" not in text


def test_database_outage_is_reported_as_503_not_500(client, monkeypatch):
    from sqlalchemy.exc import OperationalError
    from app.models import Mission

    def boom(*a, **k):
        raise OperationalError("SELECT 1", {}, Exception("connection refused"))

    monkeypatch.setattr(Mission, "query", type("Q", (), {"order_by": boom, "filter": boom, "count": boom}))
    r = client.get("/api/missions")
    assert r.status_code == 503 and "temporarily unavailable" in r.get_json()["error"]["message"]

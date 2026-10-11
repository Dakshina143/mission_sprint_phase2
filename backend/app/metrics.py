"""Prometheus metrics.

* HTTP metrics (request count, latency) are recorded per request.
* Business gauges (missions, stories, tasks, blockers, sprint points, ...) are read from the database at scrape time,
  so they always reflect persisted data. If the database is unreachable, `missionsprint_database_up` is 0 and the
  business gauges are omitted rather than reported as zero.

The registry is per application instance. Run gunicorn with one worker process (threads are fine); with several
processes each would expose only its own request counters.
"""
import time

from flask import Response, g, request
from prometheus_client import CONTENT_TYPE_LATEST, CollectorRegistry, Counter, Histogram, generate_latest
from prometheus_client.core import GaugeMetricFamily
from sqlalchemy import func, text

from .extensions import db
from .models import (ACTION_STATUS, BLOCKER_STATUS, MISSION_STATUS, SPRINT_STATUS, STORY_STATUS, TASK_STATUS, Blocker,
                     Mission, Notification, Sprint, Task, UserStory)


class DatabaseCollector:
    def __init__(self, app):
        self.app = app

    def _counts(self, model, column, values):
        rows = dict(db.session.query(column, func.count(model.id)).group_by(column).all())
        return {v: rows.get(v, 0) for v in values}

    def collect(self):
        up = GaugeMetricFamily("missionsprint_database_up", "1 if the database answered SELECT 1, else 0")
        families = []
        try:
            with self.app.app_context():
                db.session.execute(text("SELECT 1"))
                for name, doc, model, values in (
                    ("missions", "Missions by status", Mission, MISSION_STATUS),
                    ("stories", "User stories by status", UserStory, STORY_STATUS),
                    ("tasks", "Tasks by status", Task, TASK_STATUS),
                    ("blockers", "Blockers by status", Blocker, BLOCKER_STATUS),
                    ("sprints", "Sprints by status", Sprint, SPRINT_STATUS),
                ):
                    fam = GaugeMetricFamily(f"missionsprint_{name}", doc, labels=["status"])
                    for status, n in self._counts(model, model.status, values).items():
                        fam.add_metric([status], n)
                    families.append(fam)
                unread = GaugeMetricFamily("missionsprint_notifications_unread", "Unread in-app notifications")
                unread.add_metric([], Notification.query.filter_by(is_read=False).count())
                families.append(unread)
                active = Sprint.query.filter_by(status="active").first()
                if active:
                    total, done = active.points()
                    pts = GaugeMetricFamily("missionsprint_active_sprint_points", "Story points in the active sprint", labels=["kind"])
                    pts.add_metric(["total"], total)
                    pts.add_metric(["completed"], done)
                    pts.add_metric(["remaining"], total - done)
                    families.append(pts)
                db.session.rollback()
            up.add_metric([], 1)
        except Exception:
            db.session.rollback()
            families = []
            up.add_metric([], 0)
        yield up
        yield from families


def init_metrics(app):
    registry = CollectorRegistry()
    requests_total = Counter("missionsprint_http_requests_total", "HTTP requests", ["method", "endpoint", "status"], registry=registry)
    latency = Histogram("missionsprint_http_request_duration_seconds", "HTTP request latency in seconds", ["method", "endpoint"], registry=registry)
    registry.register(DatabaseCollector(app))
    app.extensions["metrics_registry"] = registry

    @app.before_request
    def _start():
        g._t0 = time.perf_counter()

    @app.after_request
    def _record(resp):
        if request.path != "/metrics" and hasattr(g, "_t0"):
            endpoint = request.url_rule.rule if request.url_rule else "unmatched"
            requests_total.labels(request.method, endpoint, str(resp.status_code)).inc()
            latency.labels(request.method, endpoint).observe(time.perf_counter() - g._t0)
        return resp

    @app.get("/metrics")
    def metrics():
        return Response(generate_latest(registry), mimetype=CONTENT_TYPE_LATEST)

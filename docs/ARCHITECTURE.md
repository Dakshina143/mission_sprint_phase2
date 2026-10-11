# Architecture notes

- **Backend**: Flask app factory (`backend/app/__init__.py`). `routes.py` (entities, sprint lifecycle, notifications),
  `analytics.py` (dashboard, charts, reports), `crud.py` (generic REST helper), `services.py` (activity log,
  notifications, progress snapshots), `validation.py`, `errors.py` (envelope + centralised handlers).
- **Response envelope**: `{"success": true, "data": ...}` or `{"success": false, "error": {"message", "details"}}`.
- **Burndown honesty**: `progress_snapshots` stores one real measurement per sprint per day, written whenever a sprint
  starts/completes or stories/tasks change. The chart's "actual" line only uses those rows (gaps carry the last measured
  value; days before the first measurement are blank). The "ideal" line is calculated and labelled as such.
- **Velocity history**: when a sprint completes, committed/delivered points are frozen on the sprint, so history survives
  stories being returned to the backlog.
- **Story/task coupling**: a story that has tasks becomes `done` when all its tasks are done, and reverts otherwise.
- **Frontend**: Vite + React. `CrudPage` drives Missions, Backlog, Sprints and Blockers; Board, Retrospectives,
  Notifications, Reports, Analytics and Dashboard are bespoke. All data comes from `src/api/client.js` (Axios,
  base URL from `VITE_API_BASE_URL`). Failures render an error state, never substitute values.
- **Auth**: intentionally not implemented in this phase (no fake auth). All endpoints are open; do not expose publicly.

## Delivery and operations (Part 2)
- **Containers**: `db` (PostgreSQL 16, named volume) → `backend` (gunicorn; entrypoint runs `flask db upgrade`, optional seed)
  → `frontend` (nginx serving the Vite build, proxying `/api/` to `backend:5000`). Start order uses health-based `depends_on`.
- **Health**: `/api/health` (readiness, real `SELECT 1`) drives the compose/Docker healthchecks and the UI indicator;
  `/api/health/live` is process liveness. The engine uses `pool_pre_ping`, so the API recovers after a database restart without a restart.
- **Metrics**: `app/metrics.py`; business gauges are computed from PostgreSQL per scrape. Prometheus (`monitoring/prometheus`) scrapes
  `backend:5000/metrics`, with four alert rules. Grafana is provisioned with the Prometheus datasource and one dashboard.
- **CI** (`.github/workflows/ci.yml`): backend tests on PostgreSQL and SQLite + migration upgrade/check/downgrade; frontend tests + build;
  Docker build and smoke test (stack + Prometheus + Grafana); `ci-ok` aggregates required results. No cloud credentials.
- **Publish/deploy** (`publish.yml`): opt-in via repository variables; GHCR push uses `GITHUB_TOKEN`; SSH deploy uses secrets and verifies the health URL.

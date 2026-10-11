# Implementation status (Parts 1 and 2)

Environment used for validation: Linux sandbox, Python 3.12.3, Node 22, **PostgreSQL 16 (real, installed locally)**, nginx,
Prometheus + promtool, actionlint, hadolint. **Docker/Docker Compose and Grafana were not available**, so images were never built here.

## Implemented
- Part 1 application (all ten feature areas) preserved.
- **Audit fixes** (found by probing on PostgreSQL): invalid/huge id filters and oversized integers caused HTTP 500 → now 422;
  story status was wrong when created into an active sprint; a failed validation could leak a half-applied change into later
  requests (rollback added); stories could join completed sprints (now 409); tasks now inherit sprint/mission from their story;
  database outages now return 503 instead of 500; `pool_pre_ping` added so the API recovers after a database restart.
- **Monitoring**: `/api/health` (real `SELECT 1`), `/api/health/live`, Prometheus `/metrics` (HTTP + DB-derived business gauges),
  Prometheus config + 4 alert rules, Grafana datasource/dashboard provisioning, 13-panel dashboard JSON.
- **Docker**: backend + frontend Dockerfiles, `docker-compose.yml` (PostgreSQL + volume, health checks, health-based startup order,
  nginx → backend proxy, optional `monitoring` profile), `.env.example`.
- **CI/CD**: `ci.yml` (tests on PostgreSQL+SQLite, migrations, frontend tests/build, Docker build + smoke test, aggregate `ci-ok`);
  `publish.yml` (opt-in GHCR publish, opt-in SSH deploy with health verification).
- **Tests**: 48 backend, 41 frontend (see below).

## Validation actually run (this sandbox)
| # | Command / check | Outcome |
|---|---|---|
| 1 | `pytest` with `TEST_DATABASE_URL` → PostgreSQL 16 | **48 passed** |
| 2 | `pytest` (in-memory SQLite) | **48 passed** |
| 3 | `pytest` with `TEST_DATABASE_URL` = non-`_test` DB | refused by guard (as designed) |
| 4 | `npm test` (Vitest + jsdom, mocked API) | **41 passed** (4 files) |
| 5 | `npm run build` | succeeded |
| 6 | `flask db upgrade` / `db check` / `seed` / `db downgrade base` / `db upgrade` on PostgreSQL | all succeeded; "No new upgrade operations detected" |
| 7 | `actionlint` on both workflows | no problems |
| 8 | `hadolint` on both Dockerfiles | clean |
| 9 | `promtool check config` | valid; 4 rules found |
| 10 | `nginx -t` with `frontend/nginx.conf` | successful |
| 11 | Compose YAML, Prometheus/Grafana YAML, dashboard JSON, entrypoint `sh -n` | parse OK |
| 12 | **Stack simulation** (run by hand, not in containers): `docker-entrypoint.sh` → gunicorn on a fresh PostgreSQL DB with `SEED_DEMO_DATA=true`; nginx with the real `nginx.conf` serving the production build | migrations ran, seed loaded; `/healthz` ok; SPA fallback 200; `/api/health` connected via nginx; `/metrics` not exposed through nginx |
| 13 | Real Prometheus scraping that backend | target `up`; `missionsprint_tasks`, `missionsprint_active_sprint_points` matched database contents; 4 rules loaded |
| 14 | PostgreSQL stopped, then restarted | `/api/health` 503, `/api/health/live` 200, `database_up` 0, `DatabaseDown` alert **pending**; after restart health 200 and `database_up` 1 without restarting the API |

## Not verified (needs your environment)
- **Docker image builds, `docker compose up`, container healthchecks and volume persistence**: Docker unavailable here. The CI `docker` job is written to verify these on GitHub's runners; **it has not run**.
- **Grafana**: dashboard JSON and provisioning parse correctly, but Grafana never loaded them; panel rendering is untested.
- **GitHub Actions**: workflows are lint-clean but have never executed on GitHub.
- **Cloud deployment / GHCR publishing**: not executed; nothing was deployed. See `MANUAL_SETUP_STEPS.md`.
- Real-browser rendering (layout, charts, drag-and-drop); frontend tests mock the API and render with jsdom.
- The `DatabaseDown` alert was seen *pending*; waiting out its 1-minute `for:` to see it *firing* was not done.
- Sandbox passwords used for local PostgreSQL are throw-away; CI uses a documented throw-away service password.

## Known limitations
- No authentication (deliberately not faked); do not expose publicly.
- Burndown history exists only from a sprint's first recorded measurement.
- Backlog reordering disabled while filtering; due-date notifications are generated when notifications are fetched.
- Metrics registry is per process, so the backend runs one gunicorn worker (threads for concurrency).
- Remaining for Part 3: the final academic report.

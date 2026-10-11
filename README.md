# MissionSprint

Agile project management connected to DevOps delivery: backlog → sprint planning → task execution → testing →
CI/CD → deployment → monitoring → retrospective.

Stack: React + Vite + Axios + React Router + Chart.js · Flask + SQLAlchemy + Flask-Migrate · PostgreSQL ·
Pytest + Vitest · Docker Compose · GitHub Actions · Prometheus + Grafana.

**Status:** see `IMPLEMENTATION_STATUS.md` (what was actually run). **Things only you can do:** `MANUAL_SETUP_STEPS.md`.

## Quick start with Docker (Windows PowerShell)
Requires Docker Desktop.
```powershell
Copy-Item .env.example .env
notepad .env                                   # set POSTGRES_PASSWORD (and SEED_DEMO_DATA=true for demo data)

docker compose build                           # build images
docker compose up -d --wait                    # start db + backend + frontend, wait until healthy
Start-Process http://localhost:8080            # the app

docker compose ps                              # status and health
docker compose logs -f backend                 # follow logs
Invoke-RestMethod http://localhost:8080/api/health
docker compose exec db psql -U missionsprint -c "\dt"

docker compose down                            # stop (data kept in the db_data volume)
docker compose down -v                         # stop AND delete the database volume
```
With monitoring (Prometheus :9090, Grafana :3000, dashboard "MissionSprint overview" is pre-provisioned):
```powershell
docker compose --profile monitoring up -d --wait
Start-Process http://localhost:3000            # Grafana (user admin, password GRAFANA_ADMIN_PASSWORD)
Start-Process http://localhost:9090/targets    # both targets should be UP
```
The browser talks only to nginx on port 8080; nginx proxies `/api` to the backend on the compose network.
The backend container applies migrations on start and (optionally) seeds demo data.

## Local development without Docker (PowerShell)
```powershell
psql -U postgres -f database\create_database.sql      # edit the password first
Copy-Item .env.example .env                            # set DATABASE_URL
cd backend; py -3.12 -m venv .venv; .\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
flask --app wsgi db upgrade; flask --app wsgi seed     # seed is optional ([DEMO] records)
flask --app wsgi run --port 5000

cd ..\frontend; Copy-Item .env.example .env; npm install; npm run dev    # http://localhost:5173
```

## Tests
```powershell
# backend (from the repository root, venv active). Default: in-memory SQLite.
pytest
# same suite on PostgreSQL: the database name MUST end in _test (tests create and drop all tables)
$env:TEST_DATABASE_URL = "postgresql+psycopg2://missionsprint:PASSWORD@localhost:5432/missionsprint_test"; pytest
# frontend
cd frontend; npm test; npm run build
```
Tests never use `DATABASE_URL`; the PostgreSQL run refuses any database not named `*_test`.

## Layout
```
backend/      Flask app, models, migrations, Dockerfile, entrypoint
frontend/     React app, Dockerfile, nginx.conf, Vitest tests (src/tests)
tests/        Backend pytest suite
database/     PostgreSQL bootstrap SQL
monitoring/   Prometheus config + alert rules, Grafana provisioning + dashboard JSON
.github/workflows/  ci.yml (tests, build, Docker smoke test) · publish.yml (optional GHCR publish + SSH deploy)
docker-compose.yml  db, backend, frontend (+ prometheus, grafana via --profile monitoring)
docs/         Architecture notes
```
Endpoints: `API_DOCUMENTATION.md`. No authentication yet: do not expose the stack to the internet as-is.

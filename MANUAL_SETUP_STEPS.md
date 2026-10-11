# Manual steps that need you

Nothing below has been done for you. Local use and CI need **no paid services and no cloud credentials**.

## 1. Run it locally with Docker (PowerShell)
1. Install Docker Desktop and start it.
2. `Copy-Item .env.example .env`, then edit `.env`: set `POSTGRES_PASSWORD` (and `GRAFANA_ADMIN_PASSWORD` for monitoring).
3. `docker compose build; docker compose up -d --wait; docker compose ps` — all services should be `healthy`.
4. Open http://localhost:8080. Optional demo data: set `SEED_DEMO_DATA=true` **before the first start**.
5. Monitoring: `docker compose --profile monitoring up -d --wait`; check http://localhost:9090/targets (backend UP) and Grafana at http://localhost:3000 → dashboard "MissionSprint overview".
6. If any step fails, send me the output of `docker compose logs --tail=100`; this stack was validated piece by piece but not inside Docker.

## 2. Push to GitHub and enable Actions
```powershell
git init -b main            # skip if this folder already has a .git directory
git add .
git status                  # confirm .env is NOT listed
git commit -m "MissionSprint"
git remote add origin https://github.com/<you>/<repo>.git     # create the empty repo on github.com first
git push -u origin main
```
- Actions run automatically on push/PR (repository **Settings → Actions → General**: allow actions). Watch the **Actions** tab; the `docker` job is the first real test of the container setup.
- Recommended: **Settings → Branches → add rule** for `main` requiring the status check **All required checks passed**.

## 3. Optional: publish images to GitHub Container Registry
- **Settings → Secrets and variables → Actions → Variables**: add `PUBLISH_IMAGES` = `true`.
- Create a tag to publish: `git tag v0.1.0; git push origin v0.1.0` (or run the workflow manually). Uses the built-in `GITHUB_TOKEN`; no extra secret.
- Packages are private by default; change visibility under your profile → Packages if you want them public.

## 4. Optional: deploy to your own Linux server (SSH)
Prerequisites on the server: Docker + Compose plugin, a folder containing this repo's `docker-compose.yml` and a `.env` (set `POSTGRES_PASSWORD`, `FRONTEND_PORT`).
Add in **Settings → Secrets and variables → Actions**:
| Type | Name | Value |
|---|---|---|
| Secret | `DEPLOY_HOST`, `DEPLOY_USER` | server address and SSH user |
| Secret | `DEPLOY_SSH_KEY` | private key of a dedicated deploy key |
| Secret | `DEPLOY_KNOWN_HOSTS` | output of `ssh-keyscan <host>` |
| Secret | `GHCR_PULL_TOKEN` | only if images are private: a token with `read:packages` |
| Variable | `DEPLOY_ENABLED` | `true` |
| Variable | `DEPLOY_PATH` | folder on the server |
| Variable | `DEPLOY_HEALTHCHECK_URL` | e.g. `https://your-host/api/health` |
Also create the `production` environment (Settings → Environments) and add required reviewers if you want manual approval.
The deploy job only reports success after the health URL answers with a connected database. Put HTTPS (a reverse proxy) in front, and note the app has **no authentication yet**.

## 5. Other decisions
- Add authentication before exposing the app beyond a trusted network.
- Set a Grafana admin password (empty falls back to Grafana's default login; ports are bound to 127.0.0.1).

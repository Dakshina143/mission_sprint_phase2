# MissionSprint API

Base URL: `http://localhost:5000/api`. JSON in/out. No authentication in this phase.

Success: `{"success": true, "data": …}` (lists may add extras such as `unread_count`, `count`).
Error: `{"success": false, "error": {"message": "…", "details": {field: "reason"} | null}}`.
Codes: 200, 201, 400 malformed body, 404 not found, 405 wrong method, 409 conflict/constraint/state, 422 validation (including bad filter values), 500 server, 503 database unavailable.

## Health and integrations
| Method | Path | Notes |
|---|---|---|
| GET | /health | Readiness: runs `SELECT 1`; 200 `{database:"connected"}` or 503 `{database:"unreachable"}` |
| GET | /health/live | Liveness: 200 whenever the process runs; never touches the database |
| GET | /metrics (no `/api` prefix) | Prometheus text format; see Monitoring below |
| GET | /integrations/cicd | `not_configured` unless `CICD_STATUS_URL` is set; then proxies its JSON `status` |

## CRUD resources
Each supports `GET /x`, `POST /x`, `GET /x/{id}`, `PUT|PATCH /x/{id}` (partial updates allowed), `DELETE /x/{id}`.
List endpoints accept `q` (text search where listed) and exact-match filters.

| Resource | Fields | Filters / search |
|---|---|---|
| /missions | title*, description, priority, status, start_date, end_date (read-only: progress, task_count) | status, priority; q |
| /sprints | name*, goal, start_date*, end_date* (status via actions below) | status; q |
| /stories | title*, description, acceptance_criteria, priority, story_points*, status, mission_id, sprint_id, rank | status, priority, mission_id, sprint_id; q |
| /tasks | title*, description, status, priority, assignee, due_date, mission_id, story_id, sprint_id | status, priority, mission_id, story_id, sprint_id, assignee; q |
| /blockers | title*, description, severity, status, reported_date, task_id | status, severity, task_id; q |
| /retrospectives | sprint_id* (one per sprint), went_well, needs_improvement (response includes action_items) | sprint_id |
| /action-items | retrospective_id*, description*, owner, status | retrospective_id, status |

Enums: priority/severity `low|medium|high|critical`; mission status `planning|active|on_hold|completed`;
story status `backlog|in_sprint|done`; task status `todo|in_progress|in_review|done`; blocker status `open|in_progress|resolved`;
action item status `open|in_progress|done`. Dates are `YYYY-MM-DD`. Unknown foreign keys return 422. Integers must fit PostgreSQL `INTEGER`; `story_points` is limited to 0–1000. Filter values on id columns must be positive integers (else 422).
Unknown JSON fields are ignored; `id`, timestamps and computed fields cannot be set.

## Actions
| Method | Path | Body | Behaviour |
|---|---|---|---|
| POST | /sprints/{id}/start | – | planned → active; 409 if another sprint is active |
| POST | /sprints/{id}/complete | `{carry_over: true}` | active → completed; freezes committed/delivered points; unfinished stories return to backlog |
| POST | /sprints/{id}/assign-stories | `{story_ids: [int]}` | Assigns stories to a non-completed sprint |
| POST | /stories/reorder | `{ids: [int]}` | Sets backlog rank by position |

## Notifications
`GET /notifications?is_read=true|false` (also generates de-duplicated due-date alerts; returns `unread_count`),
`PATCH /notifications/{id}` `{is_read}`, `POST /notifications/mark-all-read`, `DELETE /notifications/{id}`.
Types: `task_assigned`, `due_date`, `sprint_change`, `blocker`.

## Analytics and dashboard
`GET /dashboard`; `GET /analytics/burndown?sprint_id=` (defaults to active, else latest completed; `null` data if none);
`GET /analytics/velocity`; `GET /analytics/sprint-completion`; `GET /analytics/mission-progress`.

## Reports
`GET /reports/{missions|tasks|sprints|blockers|retrospectives}` → JSON `{columns, rows}`;
add `?format=csv` for a download (cells starting with `= + - @` are prefixed with `'` to prevent spreadsheet formula injection).

## Behaviour notes
- Creating a task with `story_id` inherits the story's `sprint_id` and `mission_id` when they are not given.
- A story with tasks becomes `done` when all its tasks are done and reverts when one is reopened; deleting a task re-evaluates it.
- Stories cannot be assigned to a completed sprint (409). A story assigned to an active sprint becomes `in_sprint`.
- Deleting a mission/sprint/story/task unlinks (sets null) dependants; deleting a sprint also deletes its retrospective and snapshots.
- A failed validation never persists partial changes.

## Monitoring (`GET /metrics`)
HTTP: `missionsprint_http_requests_total{method,endpoint,status}`, `missionsprint_http_request_duration_seconds` (histogram).
Read from the database at scrape time: `missionsprint_database_up`, `missionsprint_{missions,stories,tasks,blockers,sprints}{status}`,
`missionsprint_notifications_unread`, `missionsprint_active_sprint_points{kind=total|completed|remaining}` (absent when no sprint is active).
When the database is unreachable only `missionsprint_database_up 0` plus HTTP metrics are returned (no invented zeroes).
The backend runs one gunicorn worker process (with threads) so in-memory counters are complete.

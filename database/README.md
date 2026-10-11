# Database

PostgreSQL is the target database. The schema is defined by SQLAlchemy models (`backend/app/models.py`) and
versioned by Flask-Migrate/Alembic (`backend/migrations/`). Do not hand-edit tables; change the models and run
`flask db migrate` + `flask db upgrade`.

`create_database.sql` creates the role and database for local development (edit the password first).
Tables: missions, sprints, user_stories, tasks, blockers, retrospectives, action_items, notifications,
progress_snapshots (real burndown measurements), activities.

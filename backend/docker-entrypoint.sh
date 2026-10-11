#!/bin/sh
# Applies database migrations (retrying while PostgreSQL starts), optionally seeds demo data, then serves the API.
set -eu

tries=0
until flask --app wsgi db upgrade; do
  tries=$((tries + 1))
  if [ "$tries" -ge 30 ]; then
    echo "Database migration failed after $tries attempts" >&2
    exit 1
  fi
  echo "Database not ready (attempt $tries/30); retrying in 2s..." >&2
  sleep 2
done

if [ "${SEED_DEMO_DATA:-false}" = "true" ]; then
  flask --app wsgi seed
fi

# One worker process (several threads): the Prometheus request counters live in process memory.
exec gunicorn --bind 0.0.0.0:5000 --workers 1 --threads 4 --timeout 60 --access-logfile - wsgi:app

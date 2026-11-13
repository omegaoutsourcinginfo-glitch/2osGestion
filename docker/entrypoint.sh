#!/bin/sh
set -e

mkdir -p /app/data /app/media /app/staticfiles

DB_WAIT_HOST="${DB_HOST:-${POSTGRES_HOST:-}}"
DB_WAIT_PORT="${DB_PORT:-${POSTGRES_PORT:-5432}}"

should_wait_db=0
if [ -n "${DJANGO_DB_ENGINE:-}" ] || [ "${USE_POSTGRES:-0}" = "1" ]; then
  should_wait_db=1
fi

if [ "$should_wait_db" = "1" ] && [ -n "$DB_WAIT_HOST" ]; then
  echo "Waiting for database at ${DB_WAIT_HOST}:${DB_WAIT_PORT}..."
  i=0
  while [ "$i" -lt 60 ]; do
    if python - <<PY
import socket, sys
host = "${DB_WAIT_HOST}"
port = int("${DB_WAIT_PORT}")
try:
    with socket.create_connection((host, port), timeout=2):
        sys.exit(0)
except OSError:
    sys.exit(1)
PY
    then
      echo "Database is reachable."
      break
    fi
    i=$((i + 1))
    sleep 1
  done
fi

if [ "${RUN_MIGRATIONS:-1}" = "1" ]; then
  # Unfold admin checks query auth tables before they exist on first boot.
  python manage.py migrate --noinput --skip-checks
fi

if [ "${RUN_COLLECTSTATIC:-1}" = "1" ]; then
  python manage.py collectstatic --noinput --skip-checks
fi

exec "$@"

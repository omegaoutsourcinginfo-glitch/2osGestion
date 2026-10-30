#!/bin/sh
set -e

mkdir -p /app/data /app/media /app/staticfiles

# Unfold admin checks query auth tables before they exist on first boot.
python manage.py migrate --noinput --skip-checks

exec "$@"

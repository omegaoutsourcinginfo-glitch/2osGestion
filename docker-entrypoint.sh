#!/bin/sh
# Backward-compatible wrapper — prefer docker/entrypoint.sh
exec /app/docker/entrypoint.sh "$@"

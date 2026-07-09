#!/bin/sh
set -e

echo "Running database migrations..."
python -m alembic upgrade head
echo "Migrations complete. Starting uvicorn on port ${PORT:-10000}..."

exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-10000}" --proxy-headers --forwarded-allow-ips "*"
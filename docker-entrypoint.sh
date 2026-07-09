#!/bin/sh
set -e

echo "Running database migrations..."
python -m alembic upgrade head
echo "Migrations complete. Starting uvicorn..."

exec uvicorn app.main:app --host 0.0.0.0 --port 10000 --proxy-headers --forwarded-allow-ips "*"
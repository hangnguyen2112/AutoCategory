#!/bin/sh
# Initialize database and start API

echo "==> Running database migrations"
python run_migrations.py || echo "Warning: Migrations had issues but continuing..."

echo "==> Initializing database (create tables and admin user if needed)"
python init_db.py || echo "Warning: Database initialization had issues but continuing..."

echo "==> Starting API"
exec uvicorn main:app --host 0.0.0.0 --port 8000

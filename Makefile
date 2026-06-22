.PHONY: install dev migrate test lint typecheck docker-up docker-down clean

install:
	pip install -r requirements/backend.txt
	pip install -r requirements/dashboard.txt
	pip install -e ./sdk

dev:
	uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

migrate:
	alembic upgrade head

migrate-new:
	alembic revision --autogenerate -m "$(message)"

test:
	pytest tests/ -v --cov=app --cov-report=term-missing

lint:
	ruff check app/ tests/ sdk/sbn_sdk/

typecheck:
	mypy app/ sdk/sbn_sdk/

docker-up:
	docker compose up --build -d

docker-down:
	docker compose down

clean:
	rm -rf __pycache__ .pytest_cache .mypy_cache
	find . -name __pycache__ -type d -exec rm -rf {} + 2>/dev/null || true
	find . -name "*.pyc" -delete

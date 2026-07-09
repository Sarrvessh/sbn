.PHONY: install dev migrate migrate-new test lint typecheck security docker-up docker-down clean frontend-dev frontend-test frontend-build pre-commit

install:
	pip install -r requirements/backend.txt
	pip install -r requirements/dashboard.txt
	pip install -e ./sdk
	pip install pre-commit
	pre-commit install

dev:
	uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 --proxy-headers --forwarded-allow-ips "*"

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

security:
	bandit -r app/ -f json --quiet || true
	safety check -r requirements/backend.txt --full-report || true

docker-up:
	docker compose up --build -d

docker-down:
	docker compose down

frontend-dev:
	cd frontend && npm run dev

frontend-test:
	cd frontend && npm run test

frontend-build:
	cd frontend && npm run build

pre-commit:
	pre-commit run --all-files

clean:
	rm -rf __pycache__ .pytest_cache .mypy_cache
	find . -name __pycache__ -type d -exec rm -rf {} + 2>/dev/null || true
	find . -name "*.pyc" -delete
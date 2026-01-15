.PHONY: help install dev-install docker-build docker-up docker-down docker-logs migrate migrate-auto test clean

help:
	@echo "GMAO Backend - Available Commands"
	@echo "=================================="
	@echo "install         - Install production dependencies"
	@echo "dev-install     - Install dev dependencies"
	@echo "docker-build    - Build Docker images"
	@echo "docker-up       - Start Docker services"
	@echo "docker-down     - Stop Docker services"
	@echo "docker-logs     - View Docker logs"
	@echo "migrate         - Run database migrations"
	@echo "migrate-auto    - Generate new migration"
	@echo "migrate-init    - Initialize Alembic"
	@echo "test            - Run tests"
	@echo "clean           - Clean temporary files"
	@echo "format          - Format code with black"
	@echo "lint            - Lint code"

install:
	pip install uv
	uv pip install -r requirements.txt

dev-install:
	pip install uv
	uv pip install -r requirements.txt
	uv pip install pytest pytest-asyncio httpx black flake8 mypy

docker-build:
	docker-compose build

docker-up:
	docker-compose up -d
	@echo "Waiting for services to be ready..."
	@sleep 5
	@echo "Services started! API: http://localhost:8000/docs"

docker-down:
	docker-compose down

docker-logs:
	docker-compose logs -f backend

docker-clean:
	docker-compose down -v
	docker system prune -f

migrate:
	alembic upgrade head

migrate-auto:
	alembic revision --autogenerate -m "$(MSG)"

migrate-init:
	alembic revision --autogenerate -m "Initial migration"

migrate-down:
	alembic downgrade -1

migrate-history:
	alembic history

test:
	pytest -v

test-cov:
	pytest --cov=app --cov-report=html --cov-report=term

format:
	black app/ --line-length 100

lint:
	flake8 app/ --max-line-length 100
	mypy app/ --ignore-missing-imports

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type f -name "*.log" -delete
	rm -rf .pytest_cache
	rm -rf .coverage
	rm -rf htmlcov
	rm -rf *.egg-info
	rm -rf dist
	rm -rf build

dev:
	uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

backup-db:
	@echo "Creating database backup..."
	docker-compose exec db pg_dump -U gmao_user gmao_db > backup_$(shell date +%Y%m%d_%H%M%S).sql
	@echo "Backup created!"

restore-db:
	@echo "Restoring database from $(FILE)..."
	docker-compose exec -T db psql -U gmao_user gmao_db < $(FILE)
	@echo "Restore complete!"

shell:
	docker-compose exec backend bash

db-shell:
	docker-compose exec db psql -U gmao_user gmao_db

all: install docker-build docker-up migrate
	@echo "Setup complete! Access API at http://localhost:8000/docs"
.PHONY: dev test lint openapi types migrate migrate-status seed

dev:
	docker compose up --build

test:
	cd api && .venv/bin/pytest
	cd web && npm run test

lint:
	cd api && .venv/bin/ruff check .
	cd api && .venv/bin/ruff format --check .
	cd api && .venv/bin/mypy
	cd web && npx eslint . && npx prettier --check .

openapi:
	cd api && .venv/bin/python -m scripts.export_openapi

types:
	cd web && npm run types

migrate:
	cd api && .venv/bin/python -m migrations

migrate-status:
	cd api && .venv/bin/python -m migrations --status

seed:
	cd api && .venv/bin/python -m scripts.seed

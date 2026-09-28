.PHONY: test lint openapi migrate migrate-status seed

# Targets below are what Phases 1-2 (backend core, API/contract) support so
# far. `make dev` and `make types` are added in later phases (Docker/Compose,
# the React frontend) - see docs/adr/ for the plan.
#
# openapi/migrate/migrate-status/seed read config from api/.env (copy
# api/../.env.example there first) - they don't need a reachable MongoDB
# except migrate/seed, since there's no docker-compose Mongo until Phase 6.

test:
	cd api && .venv/bin/pytest

lint:
	cd api && .venv/bin/ruff check .
	cd api && .venv/bin/ruff format --check .
	cd api && .venv/bin/mypy

openapi:
	cd api && .venv/bin/python -m scripts.export_openapi

migrate:
	cd api && .venv/bin/python -m migrations

migrate-status:
	cd api && .venv/bin/python -m migrations --status

seed:
	cd api && .venv/bin/python -m scripts.seed

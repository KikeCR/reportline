.PHONY: test lint migrate migrate-status seed

# Targets below are what Phase 1 (backend core) supports so far.
# `make dev`, `make openapi`, and `make types` are added in later phases
# (API/contract pipeline, Docker/Compose) - see docs/adr/ for the plan.

test:
	cd api && .venv/bin/pytest

lint:
	cd api && .venv/bin/ruff check .
	cd api && .venv/bin/ruff format --check .
	cd api && .venv/bin/mypy

migrate:
	cd api && .venv/bin/python -m migrations

migrate-status:
	cd api && .venv/bin/python -m migrations --status

seed:
	cd api && .venv/bin/python -m scripts.seed

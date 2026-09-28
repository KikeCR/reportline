# Runbook

Operational procedures for running Reportline - there's no deployed
environment (see README's "What's simplified"), so this covers local
dev/demo operations, not production incident response.

## Migrations

- Apply pending migrations: `make migrate` (or
  `cd api && .venv/bin/python -m migrations`).
- Check what's applied: `make migrate-status`.
- Migrations are additive-only and idempotent; the runner checksums each
  applied migration's file and refuses to re-run one whose content changed
  after being applied (`MigrationChecksumMismatchError`) - this is a safety
  check against silently re-applying an edited migration, not a bug to work
  around.
  - If it fires against a database with real data, investigate why the file
    changed rather than dropping data - reformatting an already-applied
    migration file (an IDE or `ruff format` pass touching it after the fact)
    is the usual cause.
  - Against the local dev database specifically, it's always safe to resolve
    by dropping the database and re-running `python -m migrations` +
    `python -m scripts.seed`, since it holds no data worth keeping.
- `docker compose run --rm seed` runs migrations + seed as a one-off against
  the compose stack - the closest thing here to the pre-rollout init step a
  real deployment would run before rolling out `api`. There's no actual
  Kubernetes Job wired up for this: `k8s/base/` has Deployment/Service/
  ConfigMap/Secret only, verified with `kubectl kustomize`, never applied to
  a real cluster (see README's "What's simplified").

## Seeding

- `make seed` (or `cd api && .venv/bin/python -m scripts.seed`) is
  deterministic and idempotent - safe to re-run.
- `--reset` drops and recreates both demo tenants ("Acme Corporation",
  "Bramble & Co"). Needed after a migration adds or changes a required
  field, since already-seeded documents won't retroactively satisfy a new
  `$jsonSchema` validator.

## Running a sync

- Via the UI: the "Admin" tab has a button per adapter (`workday_like`,
  `bamboo_like`); it calls `POST /admin/sync/{source}` and refreshes both
  tables on completion.
- Via the API directly:
  `curl -X POST -H "X-Org-Id: <id>" http://localhost:5001/api/v1/admin/sync/workday_like`.
- Both adapters read from fixture files (`api/app/integrations/fixtures/`),
  not a live HRIS. Each fixture includes a deliberately bad record (a
  missing email, an unresolved manager reference, a manager cycle) to
  exercise quarantine - a run reporting `quarantined > 0` the first time a
  fixture is synced is expected, not a bug.
- `GET /admin/quarantine` (or the Admin tab's quarantine table) shows every
  quarantined record and why it was rejected.

## Local environment reset

If the dev Mongo container or the backend venv gets into a bad state, the
fastest clean slate:

```bash
docker rm -f reportline-dev-mongo
docker run -d --name reportline-dev-mongo -p 27017:27017 mongodb/mongodb-atlas-local:latest
cd api && .venv/bin/python -m migrations && .venv/bin/python -m scripts.seed
```

Everything this project touches locally is throwaway demo data - there's no
backup/restore procedure because there's nothing that needs preserving.

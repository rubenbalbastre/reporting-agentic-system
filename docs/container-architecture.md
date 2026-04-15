# Container Architecture

This document describes the Docker container architecture used by ReportingAgent.

## Compose Topology

The project is split into two compose files:

- `docker-compose.yml`: core app stack
- `docker-compose.langfuse.yml`: observability stack (Langfuse + dependencies)

`make up` starts both stacks together.

## Core App Stack (`docker-compose.yml`)

Services:

- `postgres` (`postgres:16-alpine`)
  - app relational database
  - host port: `${POSTGRES_PORT:-5432}`
  - persistent volume: `pg_data`
- `backend` (`python:3.12-slim`)
  - FastAPI API on port `8000`
  - installs dependencies + Playwright Chromium at startup
  - host port: `${BACKEND_PORT:-8000}`
  - mounts:
    - `./backend:/app`
    - `shared_data:/data/shared`
  - depends on healthy `postgres`
- `worker` (`python:3.12-slim`)
  - FastAPI worker API on port `5000`
  - host port: `${WORKER_PORT:-5000}`
  - mounts:
    - `./worker:/app`
    - `shared_data:/data/shared`
  - depends on healthy `postgres`
- `frontend` (`node:20-alpine`)
  - Vite dev server in container
  - container port `5173`, mapped to host `${FRONTEND_PORT:-3001}`
  - mount: `./frontend:/app`
  - depends on `backend`

## Observability Stack (`docker-compose.langfuse.yml`)

Services:

- `langfuse-web` (UI/API) exposed at host `:3002`
- `langfuse-worker` (background processing)
- `langfuse-postgres` (Langfuse DB) exposed locally at `127.0.0.1:5433`
- `langfuse-clickhouse` (analytics) exposed locally at `127.0.0.1:8123` and `127.0.0.1:9000`
- `langfuse-redis` (queue/cache) exposed locally at `127.0.0.1:6379`
- `langfuse-minio` (object storage) exposed at `:9090` and console `127.0.0.1:9091`

Persistent volumes:

- `langfuse_postgres_data`
- `langfuse_clickhouse_data`
- `langfuse_clickhouse_logs`
- `langfuse_minio_data`
- `langfuse_redis_data`

## Data/Volume Architecture

Core volumes:

- `pg_data`: app Postgres data
- `shared_data`: shared filesystem between backend and worker

Shared filesystem conventions:

- reports: `/data/shared/jobs/report_<id>/`
- skills: `/data/shared/skills/<skill_slug>/SKILL.md`

## Runtime Communication

Inside Docker network:

- frontend -> backend: `http://backend:8000` (internally; browser uses mapped host URL)
- backend -> postgres: `postgres:5432`
- backend -> worker: `http://worker:5000`
- backend/worker -> shared files: `/data/shared`

Langfuse integration:

- backend/worker send traces to `LANGFUSE_HOST` (default `http://langfuse-web:3000` on Docker network)

## Startup and Operations

Main make targets:

- `make up` / `make down`: app + Langfuse stacks
- `make stack-up` / `make stack-down`: app stack only
- `make langfuse-up` / `make langfuse-down`: Langfuse stack only
- `make ps`, `make logs`: combined stack status/logs

Database init:

- `make db-init` applies `infra/postgres/app_schema.sql` to app Postgres container.

## Health and Dependency Behavior

- `postgres` has a healthcheck (`pg_isready`).
- `backend` and `worker` wait on healthy `postgres`.
- Langfuse services use explicit health-based dependencies across postgres/minio/redis/clickhouse.


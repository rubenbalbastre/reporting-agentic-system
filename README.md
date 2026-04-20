# Reporting Agent

This is an agentic reporting app that turns chat requests into iterative markdown reports and supports reusable shared Skills.

## Product Overview

It is built around one practical loop: ask questions in chat, generate analysis and artifacts with agents, and keep a living markdown deliverable that improves turn by turn.

### Reports

Reports are the main output surface. Each report has a persistent workspace (`report_<id>`) where `report.md` and generated files evolve over time.

<img src="docs/images/ux_reports.png" alt="ReportingAgent Reports UI" width="900" />

The Reports experience is designed for iterative delivery:

- Create, iterate, and delete reports from the UI.
- Persist report conversations in Postgres (`reports -> conversations -> messages`).
- Use backend + worker agent orchestration for report generation/refinement.
- Work with any dataset, as long as it is accessible in a PostgreSQL database.

### Skills

Skills are the reusable behavior layer. Teams can teach guidance once and publish it as shared `SKILL.md` instructions for future worker runs.

Teach flow (draft creation and agent-assisted editing):

<img src="docs/images/ux_teach_skills.png" alt="ReportingAgent Teach the Agent UI" width="900" />

Library flow (published skill browsing and reuse):

<img src="docs/images/ux_skills_library.png" alt="ReportingAgent Skill Library UI" width="900" />

The Skills flow supports collaborative reuse:

- Maintain shared skills with teaching chat and publish flow.
- Persist skill conversations in Postgres (`skills -> skill_conversations -> skill_messages`).

## Setup & Run

- Docker + Docker Compose
- OpenAI API key
- Optional: Kaggle credentials for Olist dataset loading

1. Copy env file and set values:

```bash
cp .env.example .env
```

Minimum required variable:

```bash
OPENAI_API_KEY=sk-...
```

2. Start stack:

```bash
make up
```

3. Initialize app schema:

```bash
make db-init
```

4. Open services:

- Frontend: `http://localhost:3001`
- Backend API: `http://localhost:8000`
- Worker API: `http://localhost:5000`
- Langfuse UI: `http://localhost:3002`

Useful commands:

- `make up` / `make down` / `make ps` / `make logs`
- `make stack-up` / `make stack-down` / `make stack-ps` / `make stack-logs`
- `make langfuse-up` / `make langfuse-down` / `make langfuse-ps` / `make langfuse-logs`
- `make db-init` (apply `infra/postgres/app_schema.sql`)
- `make kaggle-setup` (optional Olist setup)

Run `make help` for full list.

## Architecture, API, and Data

The app exposes:

- Report APIs (create/delete reports, conversations, messages, markdown/pdf/files)
- Skill APIs (teach/publish lifecycle and skill conversations)
- Health endpoints for backend and worker
- A worker invoke endpoint used internally by backend orchestration

Data layout:

```text
/data/shared/jobs/report_<report_id>/
  report.md
  ...generated files
/data/shared/skills/<skill_slug>/SKILL.md
```

- One report can have multiple conversations.
- Deleting a report cascades to conversations/messages.
- Workspace folder cleanup is best-effort.
- `/data/shared` is backed by Docker volume `shared_data`.
- `SKILL.md` requires YAML frontmatter (`name`, `description`) and markdown instructions.
- Worker skill retrieval is keyword/frontmatter based (`search_agent_skills` + `read_agent_skill`).
- All agentic traces are logged in Langfuse for further analysis and observability.

For technical details:
- API reference: [docs/api.md](docs/api.md)
- Agent architecture: [docs/agents.md](docs/agents.md)
- Container architecture: [docs/container-architecture.md](docs/container-architecture.md)
- Reports feature: [docs/reports.md](docs/reports.md)
- Skills feature: [docs/skills.md](docs/skills.md)

## Repo Layout

```text
backend/                 FastAPI API + reporting/editor/skill agents
frontend/                React/Vite UI
worker/                  FastAPI worker + code executor agent
infra/postgres/          SQL schemas (app + Olist)
docs/                    Feature and technical docs
scripts/                 Kaggle download/load helpers
Makefile                 Main Docker/local workflow commands
```
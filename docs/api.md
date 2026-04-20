# API Reference

This document contains the current API surface for ReportingAgent.

Base URLs (default local setup):

- Backend API: `http://localhost:8000`
- Worker API: `http://localhost:5000` (internal service, typically called by backend)

## Backend API:

### Reports

#### Methods

- `GET /reports`
- `POST /reports`
- `DELETE /reports/{report_id}`
- `GET /reports/{report_id}/conversations`
- `POST /reports/{report_id}/conversations`
- `GET /conversations/{conversation_id}/messages`
- `POST /conversations/{conversation_id}/messages`
- `GET /reports/{report_id}/markdown`
- `GET /reports/{report_id}/pdf`
- `GET /reports/{report_id}/files/{file_path}`

Behavior notes:

- Creating a report also creates its first conversation.
- Sending a message to a report conversation triggers the backend orchestration flow (`reporting_agent` + tools).
- Report files are served from the report workspace via `/reports/{id}/files/{path}`.

#### Flow

For `POST /conversations/{conversation_id}/messages`:

1. Backend validates input and loads message history from Postgres.
2. Backend ensures `report.md` exists in `/data/shared/jobs/report_<id>/`.
3. Backend runs `reporting_agent` with recent conversation context.
4. `reporting_agent` may call `worker_agent` for analysis/artifact generation.
5. `reporting_agent` uses `editor_agent` to write/update `report.md` and references.
6. Backend stores user + assistant messages in `messages`.
7. Frontend refreshes chat and report markdown preview.

### Skills

#### Methods

- `GET /skills`
- `POST /skills`
- `DELETE /skills/{skill_id}`
- `GET /skills/{skill_id}/markdown`
- `GET /skills/{skill_id}/conversations`
- `POST /skills/{skill_id}/conversations`
- `GET /skill-conversations/{skill_conversation_id}/messages`
- `POST /skill-conversations/{skill_conversation_id}/messages`
- `POST /skills/{skill_id}/publish`

Behavior notes:

- Creating a skill also creates its first skill conversation.
- `GET /skills/{skill_id}/markdown` returns `404` until a publish has generated `SKILL.md`.
- Publish updates skill metadata (`name`, `description`, `slug`, `skill_md_path`, `updated_at`).

#### Flow

[to fill]

## Worker Internal API

- `POST /invoke`

Notes:

- This endpoint is designed for backend-to-worker use.
- `result` is derived from worker structured output:
  - clarification prompt when status is `needs_more_info`
  - execution summary when status is `ready_to_execute`

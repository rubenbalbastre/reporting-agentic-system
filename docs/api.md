# API Reference

This document contains the current API surface for ReportingAgent.

Base URLs (default local setup):

- Backend API: `http://localhost:8000`
- Worker API: `http://localhost:5000` (internal service, typically called by backend)

## Reports

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

## Skills

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

## Compatibility Endpoints

- `POST /agent/teach` (legacy quick-save flow)
- `GET /agent/skills` (legacy compatibility listing)

## Health

- Backend: `GET /health`
- Worker: `GET /health`

## Worker Internal Endpoint

- `POST /invoke`

Request body:

```json
{
  "query": "string",
  "report_id": 123
}
```

Response body:

```json
{
  "result": "string",
  "session_id": "report_123"
}
```

Notes:

- This endpoint is designed for backend-to-worker use.
- `result` is derived from worker structured output:
  - clarification prompt when status is `needs_more_info`
  - execution summary when status is `ready_to_execute`

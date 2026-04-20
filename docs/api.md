# API Reference

This document lists the current HTTP API surface.

Use this as a concise developer reference. For product behavior and UX, start with `docs/reports.md` and `docs/skills.md`.

Base URLs in local Docker setup:

- Backend API: `http://localhost:8000`
- Worker API: `http://localhost:5000`

## Backend API

### Health

- `GET /health`

Returns:

```json
{ "status": "ok", "service": "backend" }
```

### Reports

- `GET /reports`
  List reports.

- `POST /reports`
  Create a report.

Request:

```json
{ "title": "New Report" }
```

Notes:

- If `title` is blank, backend uses `"New Report"`.
- Creating a report also creates its first conversation and starter `report.md`.

- `POST /reports/{report_id}/title`
  Rename a report.

Request:

```json
{ "title": "Renamed Report" }
```

- `DELETE /reports/{report_id}`
  Delete a report and its workspace folder on a best-effort basis.

- `GET /reports/{report_id}/conversations`
  List conversations for one report.

- `POST /reports/{report_id}/conversations`
  Create a conversation for one report.

- `GET /conversations/{conversation_id}/messages`
  List messages for one conversation.

- `POST /conversations/{conversation_id}/messages`
  Append a user message and run the reporting flow.

Request:

```json
{ "content": "Analyze revenue by category." }
```

Response:

```json
{
  "messages": [
    {
      "id": 1,
      "report_id": 1,
      "role": "user",
      "content": "Analyze revenue by category.",
      "created_at": "2026-04-20T10:00:00Z"
    },
    {
      "id": 2,
      "report_id": 1,
      "role": "assistant",
      "content": "I updated the report.",
      "created_at": "2026-04-20T10:00:03Z"
    }
  ]
}
```

Notes:

- Blank `content` returns `400`.
- Backend stores both the user and assistant messages.
- If agent execution fails, the user message is still stored and the assistant message becomes a fallback error string.

- `GET /reports/{report_id}/markdown`
  Return report markdown.

Response:

```json
{ "content": "# Report title\n..." }
```

- `GET /reports/{report_id}/pdf`
  Export the current report as PDF.

Notes:

- This endpoint depends on Playwright Chromium in the backend runtime.
- If Chromium is unavailable or broken, PDF export returns an error even if the rest of the app is healthy.

- `GET /reports/{report_id}/files/{file_path}`
  Serve a file from the report workspace.

## Skills API

- `POST /agent/teach`
  Create a shared skill directly from one teaching prompt.

Request:

```json
{ "content": "Teach the agent how to compare monthly revenue by category." }
```

Response:

```json
{
  "message": "Skill created and stored in shared volume",
  "skill_filename": "SKILL.md",
  "skill_path": "/data/shared/skills/.../SKILL.md"
}
```

- `GET /agent/skills`
  List skills discoverable by the worker.

- `GET /skills`
  List skill records.

- `POST /skills`
  Create a draft skill.

Request:

```json
{ "name": "New Skill" }
```

Notes:

- Blank `name` returns `400`.
- Creating a skill also creates its first skill conversation and draft `SKILL.md`.

- `DELETE /skills/{skill_id}`
  Delete a skill and its filesystem directory on a best-effort basis.

- `GET /skills/{skill_id}/markdown`
  Return current draft or published `SKILL.md`.

Response:

```json
{ "content": "---\nname: ...\n---\n..." }
```

- `GET /skills/{skill_id}/files`
  List files inside the skill package directory.

Response:

```json
{ "files": ["SKILL.md", "examples/"] }
```

- `POST /skills/{skill_id}/open-draft`
  Create a new draft from a published skill package.

- `GET /skills/{skill_id}/conversations`
  List conversations for one skill.

- `POST /skills/{skill_id}/conversations`
  Create a conversation for one skill.

- `GET /skill-conversations/{skill_conversation_id}/messages`
  List messages for one skill conversation.

- `POST /skill-conversations/{skill_conversation_id}/messages`
  Append a user message and run the skill teaching flow.

Request:

```json
{ "content": "Add stricter rules for missing category labels." }
```

Response:

```json
{
  "messages": [
    {
      "id": 1,
      "skill_id": 1,
      "skill_conversation_id": 1,
      "role": "user",
      "content": "Add stricter rules for missing category labels.",
      "created_at": "2026-04-20T10:00:00Z"
    },
    {
      "id": 2,
      "skill_id": 1,
      "skill_conversation_id": 1,
      "role": "assistant",
      "content": "I updated the draft accordingly.",
      "created_at": "2026-04-20T10:00:03Z"
    }
  ]
}
```

Notes:

- Blank `content` returns `400`.
- Published skills are read-only; sending messages to them returns `400`.

- `POST /skills/{skill_id}/publish`
  Publish a draft skill package.

Request:

```json
{ "skill_conversation_id": 1 }
```

Notes:

- `skill_conversation_id` is optional. If omitted, backend uses the latest conversation for the skill.
- Publish updates `name`, `description`, `slug`, `skill_md_path`, and `updated_at`.

## Worker Internal API

### Health

- `GET /health`

Returns:

```json
{ "status": "ok", "service": "worker" }
```

### Invoke

- `POST /invoke`

Used internally by backend agents.

Request:

```json
{
  "query": "Compute monthly revenue by category and save a chart.",
  "task_type": "report",
  "report_id": 42
}
```

Fields:

- `query` required
- `task_type` is `"report"` or `"skill"`, default `"report"`
- one of `report_id`, `session_id`, or `workspace_path` must be present

Response:

```json
{
  "result": "Summary or clarification text",
  "session_id": "report_42"
}
```

Notes:

- Skill requests require `workspace_path`.
- Worker validates that `workspace_path` stays under allowed shared roots.
- `result` is flattened from the worker agent structured output:
  - clarification question when more info is needed
  - execution summary when ready to proceed

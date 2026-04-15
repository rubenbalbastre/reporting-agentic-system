# Reports

This document describes the Reports feature and current behavior.

## Overview

Reports are workspace-scoped markdown outputs that evolve through chat.
The app is expected to work with any dataset, as long as it is available in a PostgreSQL database the worker can access.

## Purpose

Reports are the app's core delivery feature: they provide a persistent output workspace where users iteratively refine analysis and narrative through chat while preserving report context and generated artifacts.

UI layout:

- Left: reports list
- Center: report preview (`report.md`)
- Right: report chat

## Data Model

Database tables:

- `reports`
- `conversations`
- `messages`

Relations:

- `reports -> conversations` (`ON DELETE CASCADE`)
- `conversations -> messages` (`ON DELETE CASCADE`)

This allows multiple conversations for a single report workspace.

Implementation detail:
- Creating a report inserts one initial conversation automatically.

## Workspace Mapping

Each report has a folder in shared storage:

```text
/data/shared/jobs/report_<report_id>/
  report.md
  ...generated files
```

`report.md` is served to the preview UI.

Initial content:
- New reports get a starter markdown with title, report id, and creation timestamp.

## Agentic Flow

When sending `POST /conversations/{conversation_id}/messages`:

1. Backend loads conversation history and ensures `report.md` exists.
2. Backend runs `main_agent` (model `gpt-5.4-mini`).
3. `main_agent` can use:
   - `call_artifact_worker` -> `POST /invoke` on worker with `{query, report_id}`.
   - `report_agent` -> workspace-safe tools to read/update `report.md` and files.
4. Worker `/invoke` runs `code_executor_agent` (model `gpt-5.4-mini`) with tools for:
   - file operations in `report_<id>/`
   - Python execution (`run_python`)
   - PostgreSQL inspection helpers
   - shared skill search/read
5. Backend stores user and assistant messages in `messages`.

Worker result contract:
- `needs_more_info`: backend receives a clarification question with missing info.
- `ready_to_execute`: backend receives a short execution summary.

## Backend API

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

## UX Actions

Sidebar actions:

- `+` create report
- `🗑` delete active report

Chat actions:

- select conversation
- create new conversation (`✏️`)
- send message

View controls:

- Original View
- Expand Report
- Expand Chat
- Export PDF (from Report Preview header)

## Delete Behavior

Deleting a report:

1. Removes row from `reports`.
2. Removes related `conversations` and `messages` through cascade.
3. Performs best-effort deletion of workspace folder `report_<id>`.

## Notes

- Report preview renders markdown and supports embedded files via `/reports/{id}/files/{path}`.
- PDF export renders the current report markdown (including report workspace images) through Playwright Chromium.
- Main page scrolling is disabled; each panel scrolls independently.

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

## Workspace Mapping

Each report has a folder in shared storage:

```text
/data/shared/jobs/report_<report_id>/
  report.md
  ...generated files
```

`report.md` is served to the preview UI.

## Backend API

- `GET /reports`
- `POST /reports`
- `DELETE /reports/{report_id}`
- `GET /reports/{report_id}/conversations`
- `POST /reports/{report_id}/conversations`
- `GET /conversations/{conversation_id}/messages`
- `POST /conversations/{conversation_id}/messages`
- `GET /reports/{report_id}/markdown`
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

## Delete Behavior

Deleting a report:

1. Removes row from `reports`.
2. Removes related `conversations` and `messages` through cascade.
3. Performs best-effort deletion of workspace folder `report_<id>`.

## Notes

- Report preview renders markdown and supports embedded files via `/reports/{id}/files/{path}`.
- Main page scrolling is disabled; each panel scrolls independently.

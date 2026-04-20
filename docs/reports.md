# Reports

This document is the product-level entry point for the Reports experience.

## What It Is

Reports are the main output surface of the app. A report is a persistent markdown deliverable that improves over time through chat.

The product loop is simple:

1. Create or select a report.
2. Ask for analysis, refinements, or charts in chat.
3. Review the updated markdown preview.
4. Continue iterating until the report is ready to export.

The app is designed for datasets available in a PostgreSQL database the worker can access.

## Main Screen

The main application screen is organized into three areas:

- Left: report list
- Center: report preview
- Right: report chat

At the top of the page the user can:

- switch between `Original`, `Report`, and `Chat` views
- open `Skill Library`
- open `Teach the Agent`

Inside the Reports area, the user can:

- create a report
- rename a report
- delete a report
- switch between conversations
- create a new conversation
- export the current report as PDF

## User Flow

### Create and Start

Creating a report immediately creates:

- a report record
- an initial conversation
- a starter `report.md`

This means a newly created report is ready to use without extra setup.

### Work Through Chat

The chat is the control surface for the report. A user can ask the agent to:

- refine wording or structure
- add new analysis
- generate charts or tables
- expand existing sections
- answer follow-up questions inside the same report context

Each message updates the same report workspace, so the report behaves like a living deliverable instead of a one-shot answer.

### Use Conversations

Each report can have multiple conversations.

This is useful when a user wants to:

- explore different directions for the same report
- keep one conversation for a broad draft and another for a specific analysis
- preserve earlier threads without mixing all requests together

Conversations belong to the same report workspace. They change the chat history, not the report identity.

### Review the Preview

The middle panel renders the current markdown from `report.md`.

This is the main reading surface for the product. It lets the user verify:

- structure
- wording
- generated images
- tables and code blocks

If the markdown references report files, the preview resolves them from the report workspace.

### Export

When the report is ready, the user can export it as PDF from the report preview header.

The PDF export is based on the current markdown state, so the preview and exported document are aligned.

## UX Notes

- `Original` shows the standard two-panel report + chat layout.
- `Report` focuses on the preview panel only.
- `Chat` focuses on the conversation panel only.
- If no report is selected, the empty state prompts the user to create or select one first.
- If a conversation has no messages yet, the UI encourages the user to ask for refinements, analyses, or charts.

## What Gets Persisted

A report persists in two forms:

- relational state in PostgreSQL
- files in the shared workspace

Database entities:

- `reports`
- `conversations`
- `messages`

Workspace layout:

```text
/data/shared/jobs/report_<report_id>/
  report.md
  ...generated files
```

What this means in product terms:

- the report identity lives in the database
- the report content lives in `report.md`
- generated artifacts such as figures live beside the report in the same workspace

Deleting a report removes its DB state and performs best-effort cleanup of the workspace folder.

## How The Product Works Internally

When a user sends a message:

1. Backend loads the conversation history.
2. Backend ensures `report.md` exists.
3. `reporting_agent` decides how to respond.
4. The agent can call the worker to inspect data or generate artifacts.
5. The agent can update the report workspace.
6. Backend stores the user and assistant messages.
7. Frontend refreshes both chat and preview.

The important product behavior is that the report is not just chat output. It is a persistent file-backed workspace that the agents keep updating.

## Limitations

- Report quality depends on what the worker can access in PostgreSQL.
- The preview is markdown-first, so the product is optimized for document-style outputs rather than arbitrary app UIs.
- PDF export depends on the current rendering pipeline and Playwright Chromium availability.

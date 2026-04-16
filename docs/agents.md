# Agents Architecture

This document explains the current agent architecture used by ReportingAgent.

## Overview

The report chat flow is orchestrated by a backend `main_agent` that coordinates:

- a report-editing tool agent (`report_agent`)
- a worker execution service (`POST /invoke`) that runs `code_executor_agent`

Skills are managed by dedicated backend agents for teaching and publishing.

## Agent Roles

### `main_agent` (backend)

- Built in `backend/app/agents/main_agent.py`
- Model: `gpt-5.4-mini`
- Purpose: orchestrate report responses from chat input
- Tools:
  - `report_agent`: edits `report.md` and workspace files safely
  - `call_artifact_worker(content)`: calls worker `POST /invoke` with `{query, report_id}`

### `report_agent` (backend tool-agent)

- Built in `backend/app/agents/report_agent.py`
- Model: `gpt-5.4-mini`
- Purpose: deterministic report/workspace editing for one report workspace
- Key tools:
  - `read_report`, `update_report`, `update_report_section`
  - `list_files`, `read_file`, `replace_in_file`
  - `build_report_file_url` (canonical `/reports/{id}/files/<path>` links)
- Safety:
  - all file paths resolve inside `report_<id>` workspace
  - binary file reads are blocked (images can be uploaded for reasoning)
  - image markdown paths are normalized to backend file URLs

### `code_executor_agent` (worker)

- Built in `worker/app/agents/code_executor_agent.py`
- Model: `gpt-5.4-mini`
- Triggered by worker `POST /invoke`
- Purpose: inspect DB/files, write and run Python, generate report artifacts
- Key tools:
  - workspace file ops: `write_file`, `read_file`, `replace_in_file`, `list_files`
  - execution: `run_python`
  - PostgreSQL inspection: `get_database_schema`, `get_unique_values`, `get_column_stats`, `preview_table`
  - shared skills: `search_agent_skills`, `read_agent_skill`
- Output contract (`CodeAgentResult`):
  - `status = needs_more_info` with clarification question + missing info list
  - `status = ready_to_execute` with summary

### Skills Agents (backend)

- `main_skill_agent` (`gpt-5.4-mini`): orchestrates skill generation and can only call the worker code executor tool (`POST /invoke`) with a skill session workspace.

## End-to-End Report Message Flow

For `POST /conversations/{conversation_id}/messages`:

1. Backend validates input and loads message history from Postgres.
2. Backend ensures `report.md` exists in `/data/shared/jobs/report_<id>/`.
3. Backend runs `main_agent` with recent conversation context.
4. `main_agent` may call worker `/invoke` for analysis/artifact generation.
5. `main_agent` uses `report_agent` to write/update `report.md` and references.
6. Backend stores user + assistant messages in `messages`.
7. Frontend refreshes chat and report markdown preview.

## Service Boundaries

- Backend (`:8000`):
  - user-facing REST API
  - orchestration and skill lifecycle
  - report markdown/PDF/file serving
- Worker (`:5000`):
  - internal execution endpoint (`/invoke`)
  - code/data/artifact generation in report workspace

## Storage Model

- Report workspace:
  - `/data/shared/jobs/report_<report_id>/report.md`
  - generated artifacts (commonly under `figures/`)
- Shared skills:
  - `/data/shared/skills/<skill_slug>/SKILL.md`
- Postgres state:
  - reports/conversations/messages
  - skills/skill_conversations/skill_messages

## Models In Use

- `main_agent`: `gpt-5.4-mini`
- `report_agent`: `gpt-5.4-mini`
- `code_executor_agent`: `gpt-5.4-mini`
- `main_skill_agent`: `gpt-5.4-mini`

## Design Decisions

### Planner + Executor (initial design)

At the beginning, the coding flow was designed with two specialized agents:

- a planner agent
- an executor agent

The goal was to separate reasoning/planning from implementation/execution.

### What traces showed after one week

After roughly one week of trace analysis, results were not optimal in this project setup:

- repeated tool calls appeared frequently without adding new information
- context was partially lost between agent handoffs/calls
- extra round-trips increased latency and token usage

In practice, this produced higher cost and slower responses, with inconsistent quality gains.

### Current decision: unified coding agent

The planner/executor split was replaced with a unified `code_executor_agent`.

This change reduced:

- end-to-end latency
- token/call overhead (cost)

And it improved task outcomes for this codebase.

### Model-family caveat

These gains are tied to the current GPT-5.4 family behavior.

For older model families, a two-agent split (planner + executor) may still be beneficial depending on task complexity and context-window behavior.

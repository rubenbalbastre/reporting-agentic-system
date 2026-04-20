# Agents Architecture

This document explains the current agent architecture behind ReportingAgent.

## Overview

The system is organized around four agents:

- `reporting_agent`: owns the report chat experience
- `skill_agent`: owns the skill teaching experience
- `editor_agent`: edits report files safely inside one report workspace
- `code_agent`: inspects data, writes code, runs Python, and produces artifacts inside the worker

The two user-facing agents live in the backend:

- `reporting_agent`
- `skill_agent`

The execution-heavy agent lives in the worker service:

- `code_agent`

`editor_agent` is a specialized helper used by `reporting_agent`.

## Agent Roles

### `reporting_agent`

- Built in `backend/app/agents/reporting_agent.py`
- Model: `gpt-5.4-mini`
- Purpose: orchestrate report responses from chat input
- Main tools:
  - `editor_agent` for report and workspace updates
  - worker invocation through `POST /invoke`

This agent is responsible for turning report chat messages into coordinated actions. It decides when a request needs:

- direct report editing
- data exploration or artifact generation in the worker
- both

### `editor_agent`

- Built in `backend/app/agents/editor_agent.py`
- Model: `gpt-5.4-mini`
- Purpose: perform controlled edits inside a single report workspace

Key tools:

- `read_report`
- `update_report`
- `update_report_section`
- `list_files`
- `read_file`
- `replace_in_file`
- `build_report_file_url`

Safety properties:

- all paths resolve inside `report_<id>`
- binary file reads are blocked as text
- images can be uploaded for visual reasoning when needed
- markdown image paths are normalized to backend file URLs

This separation keeps report editing deterministic and scoped, instead of giving the worker direct ownership of the final report markdown.

### `skill_agent`

- Built in `backend/app/agents/skill_agent.py`
- Model: `gpt-5.4-mini`
- Purpose: orchestrate skill teaching and draft refinement
- Main tool:
  - worker invocation through `POST /invoke`

Unlike `reporting_agent`, `skill_agent` does not use a dedicated editor helper. Its role is narrower: it drives the teaching conversation and delegates code or file-oriented work to the worker in a skill workspace.

### `code_agent`

- Built in `worker/app/agents/code_agent.py`
- Model: `gpt-5.4-mini`
- Triggered by worker `POST /invoke`
- Purpose: inspect data, write files, run Python, and generate artifacts

Key tools:

- workspace file operations:
  - `write_file`
  - `read_file`
  - `replace_in_file`
  - `list_files`
- execution:
  - `run_python`
- PostgreSQL inspection:
  - `get_database_schema`
  - `get_unique_values`
  - `get_column_stats`
  - `preview_table`
- shared skill access:
  - `search_agent_skills`
  - `read_agent_skill`

Output contract:

- `status = needs_more_info` with a clarification question and missing information list
- `status = ready_to_execute` with a summary

## Workspaces

Agents are connected to persistent workspaces.

For reports:

- `/data/shared/jobs/report_<report_id>/report.md`
- generated artifacts, commonly under `figures/`
- helper scripts or temporary files created by the worker

For skills:

- draft skills: `/data/shared/skills_drafts/<draft_slug>/SKILL.md`
- published skills: `/data/shared/skills/<skill_slug>/SKILL.md`

Conversational state lives in PostgreSQL:

- `reports -> conversations -> messages`
- `skills -> skill_conversations -> skill_messages`

### Why a persistent worker container

The worker was implemented as a persistent Docker service instead of spawning a fresh isolated container per task. The main reason was simplification:

- every worker call is just `POST /invoke`
- no separate container lifecycle management or cleanup layer was needed
- local development and debugging are much easier with a long-lived service
- implementation overhead stayed low for an early product version

This is not the strongest isolation model, but for this project the operational simplicity was worth more than per-task container isolation.

### Why shared Docker volumes

Backend and worker communicate through the `shared_data` Docker volume mounted at `/data/shared`.

This was chosen as a pragmatic way to share:

- report files
- generated artifacts
- skill packages
- skill drafts

The tradeoff is that Docker shared volumes are not especially fast, particularly for many small file operations. Even with that limitation, the approach was kept because it simplified the system substantially:

- both services can read and write the same workspaces directly
- report markdown, images, scripts, and skill files are immediately visible to both containers
- the implementation stays easy to reason about because paths are ordinary filesystem paths
- persistence across container restarts comes for free through the Docker volume

In short, shared volumes were slower than a more specialized storage design, but they were good enough for the workload and much simpler to build and operate.

## Design Decisions

### Models

This project uses OpenAI models because the main goal was to build a reproducible agentic application quickly with tools and traces that were already familiar in this stack.

The chosen family is `gpt-5.4`, mainly `gpt-5.4-mini`, because it provided the best balance of:

- capability
- latency
- cost

The larger model was not adopted because the extra cost was not justified for the current scope.

### Framework

The project uses the OpenAI Agents SDK.

The main reason was fit: the product needed agents that could run tools until they reached a final answer, without introducing a more complex orchestration framework than necessary. A framework such as LangGraph could also work here, but the current architecture did not require that extra complexity.

### Tools

The worker tools were designed to mirror what an analyst would need in practice.

For database understanding:

- `get_database_schema`
- `get_unique_values`
- `get_column_stats`
- `preview_table`

For filesystem work:

- `write_file`
- `read_file`
- `replace_in_file`
- `list_files`

For execution:

- `run_python`

For shared skill reuse:

- `search_agent_skills`
- `read_agent_skill`

The worker intentionally runs Python rather than exposing a general shell environment. That kept the system narrower, easier to reason about, and sufficient for the current workload.

## System Design Decisions

### Planner + Executor vs Unified `code_agent`

An earlier design split the worker flow into:

- a planner agent
- an executor agent

That design increased handoffs and often repeated work without improving outcomes enough to justify the cost. In practice it led to:

- repeated tool calls
- partial context loss between agent boundaries
- extra latency and token cost

The final design uses one unified `code_agent`, which improved reliability and reduced overhead for this codebase.

### Database Agent vs Database Tools

An earlier design also included a dedicated database agent. That approach caused database exploration to happen more than once:

1. once in the database agent
2. again in the code agent during real execution

The final design removed the database agent and gave those capabilities directly to `code_agent`.

### Why `editor_agent` Exists

Editing the final report is different from generating intermediate artifacts.

Report editing involves:

- structured markdown updates
- section-aware changes
- file references
- image path normalization

Keeping that work in `editor_agent` improved traceability and kept the worker focused on analysis and artifact generation. It may use more tokens than a single-agent design, but it produced a cleaner separation of concerns for this project.

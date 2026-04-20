# Agents Architecture

This document explains the current agent architecture used in the application.

## Overview

There are two agents which directly interact with the user: `reporting_agent` and `skill_agent`, which live in the backend project folder where the main API is implemented. We might refer to them in the further text as main agents. Here, also relies `editor_agent`, which is used as a tool by the `reportding_agent`. Both main use several tools and an agent as a tool named `worker_agent`, which has its own project folder `/worker/` and API.

Then, the project contains four agents:

- `reporting_agent`: a report-editing agent. Owner of the Reports product part.
- `skill_agent`: a skill-editing agent. Owner of the Skills product part.
- `worker_agent`: a code agent which owns the creation of artifacts and any code scripts requires for the app to satisfy a user request.
- `editor_agent`: an agent which edits the report based on worker_agent results and conversation context.

## Agents

In this section, a technical description of each agent is provided.

### Report Agents

#### `reporting_agent`

- Built in `backend/app/agents/reporting_agent.py`
- Model: `gpt-5.4-mini`
- Purpose: orchestrate report responses from chat input
- Tools:
  - `editor_agent`: edits `report.md` and workspace files safely
  - `worker_agent`: it is called thought a `POST (invoke)` request to the worker API.

#### `editor_agent`

- Built in `backend/app/agents/editor_agent.py`
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

### Skills Agents

#### `skill_agent` 
- Built in `backend/app/agents/skill_agent.py
- Model: `gpt-5.4-mini`
- Purpose: orchestrates skill generation and can only call the worker code executor tool (`POST /invoke`) with a skill session workspace.
- Key tools:


### Cross Agents

#### `code_agent`

- Built in `worker/app/agents/code_agent.py`
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


## Workspaces

Agents are connected to specific workspaces based on the Report they are working on. For the Report agent:
- `/data/shared/jobs/report_<report_id>/report.md`
- generated artifacts (commonly under `figures/`)
- other scripts

For Skills:
- `/data/shared/skills/<skill_slug>/SKILL.md`

For conversational data, postgres state:
  - reports/conversations/messages
  - skills/skill_conversations/skill_messages


## Design Decisions

### Models

Since this project prioritizes reproducibility in most environments as possible, closed-models where selected for this project. Due to my personal familiarity with OpenAI models I decided to go with it. However, Antrophic and other providers could have serve the same purpose.

From OpenAI models, I wanted to go with the SOTA (as-april-2026) so gpt-5.4 models family was chosen. I tried the nano and mini versions, having mini a best overall performance and balancing the cost/performance trade-off properly. Note that a message could cost approximately 0.04$ when starting a basic report from scrath with mini version. The larger version was not tested due to higher costs.

An important reason to select those models was the will of using agent oriented models and not just intruction based ones. Note that the last families of GPT models are more oriented to agentic task and long-term runs.

### Framework

Among Agents frameworks like LangGraph, this project uses OpenAI Agents SDK. Agents are executed until the stop using tools and generate a final output. This feature satisfied the project requirements and no extra complexity was required. Here, we also lie on the assumption of usage of OpenAI closed models. However, there no exist a critical reason not to change to other framework if desired.

### Tools

In other for the agents to have success they should mirror what an analyst would make One of the first things to provide is **access to explore the database** the agents are supposted to report on. To make this available several functions are provided:

- get_database_schema
- get_unique_values
- get_column_stats
- preview_table

Also, it requires to be able to **list, create, edit and delete files**, plus being able to execute code. For simplicity, it is only able to **run python code** so consequently it only generates python code. Full access to the shell commands was not provided since it was not needed.

- write_file
- read_file
- replace_in_file
- list_files
- run_python

To **interact with the created Skills** in the app, there are defined two more tools for the worker agent to call:

-  search_agent_skills,
-  read_agent_skill,

### System Design

#### Code agent: Planner + Executor (initial design) -> unified agent (final design)

At the beginning, the coding flow was designed with two specialized agents:

- a planner agent
- an executor agent

The goal was to separate reasoning/planning from implementation/execution.However, after roughly one week of trace analysis, results were not optimal in this project setup:

- repeated tool calls appeared frequently without adding new information
- context was partially lost between agent handoffs/calls
- extra round-trips increased latency and token usage

In practice, this produced higher cost and slower responses, with inconsistent quality gains. The planner/executor split was replaced with a unified `code_agent`, which reduced:

- end-to-end latency
- token/call overhead (cost)

And it improved task outcomes for this codebase.

#### Database Agent vs Database tools for Code Agent

Initially, a database agent was defined to explore database and inform if a user query was possible to answer or not. However, this implementation implied that database was queried several times: 1) for the database agent to answer and 2) for the code agent to properly work on database data. For this reason, database agent was removed and their tools were given to the Code Agent.

#### Editor Agent

Editing a report which consists of processing markdown file and images (multi-modality implied) required specific context and tools which was simpler to have issolated to have a better tracebility. Despite, it might use more tokens that leaving the Code Agent to handle this it would have given too much context for the Code Agent to work. Since no critical latency and cost increase was found, this was the final choice. 
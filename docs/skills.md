# Skills in ReportingAgent

This document describes the Skills feature added in this branch.

## Overview

Skills are reusable instructions learned from user text. They are created through the UI and stored in the shared Docker volume so worker agents can apply them in future tasks.

## Storage

Skills are stored in:

```text
/data/shared/skills/<skill_name>/SKILL.md
```

`/data/shared` is backed by the `shared_data` Docker volume.

## SKILL.md format

Each skill must define YAML frontmatter and Markdown instructions.

```md
---
name: pdf-processing
description: Extract PDF text, fill forms, merge files. Use when handling PDFs.
---

# PDF Processing

## When to use this skill
Use this skill when the user needs to work with PDF files...
```

Frontmatter keys used by the system:

- `name` (required)
- `description` (required)

## API

Backend endpoints:

- `POST /agent/teach`
  - Input: free-text user instruction
  - Behavior: runs `skill_agent` to generate structured skill content and persists `SKILL.md`
- `GET /agent/skills`
  - Returns existing skills for UI listing (skill id, name, description, SKILL.md path)

## UI behavior

- Top bar includes `Teach the Agent`.
- Clicking opens the teach modal.
- Existing skills are hidden by default.
- User can click `Show learnt skills` to fetch and display skills.
- Saving a skill refreshes the list if it is visible.

## Agent usage model

- Main interface agent does not consume skills directly.
- Worker code planner:
  - Searches and reads relevant skills.
  - Adds selected skills and usage notes into the execution plan.
- Worker code executor:
  - Receives planner skill notes.
  - Can also search/read skills during execution when needed.

## Prompt ownership

Prompt templates are centralized in:

- `backend/app/prompts.py` for backend agents, including `skill_agent`
- `worker/app/prompts.py` for planner/executor worker agents

## Current limitation

The current implementation is intentionally basic: skill creation persists only a single `SKILL.md` file in each skill directory. It does not yet generate richer skill packages such as `scripts/`, `references/`, `assets/`, or advanced multi-file examples/instructions. This is a good candidate for a future pull request.

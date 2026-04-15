# Skills (Shared)

This document describes the current shared Skills implementation.

## Overview

Skills are reusable instructions learned through the `Teach the Agent` UI.

## Purpose

Skills are the app's reusable behavior feature: they let users teach domain/process guidance once and persist it as shared instructions that worker agents can apply in future tasks.

Key design decision:

- Skills are intended for worker agents (code executor flow).
- Main interface agent does not directly consume shared skills; the worker code executor does.

Current agent roles:
- `skill_chat_agent` (`gpt-5.4-nano`) powers skill teaching chat turns.
- `skill_agent` (`gpt-5.4-nano`) generates publish payload JSON (`skill_name`, `description`, `skill_markdown`).

## Storage

Skills are stored in the shared Docker volume:

```text
/data/shared/skills/<skill_slug>/SKILL.md
```

`/data/shared` is backed by Docker volume `shared_data`.

## File Structure

Current implementation writes only one file:

```text
<skill_slug>/
  SKILL.md
```

If a generated skill directory already exists, publish/create uses a timestamp suffix (for example `my-skill-20260415_102000`) to avoid collisions.

Future extension may include:

```text
my-skill/
  SKILL.md
  scripts/
  references/
  assets/
```

## SKILL.md Format

Frontmatter is assumed present and includes at least:

- `name`
- `description`

Example:

```md
---
name: pdf-processing
description: Extract PDF text, fill forms, merge files. Use when handling PDFs.
---

# PDF Processing

## When to use this skill
Use this skill when the user needs to work with PDF files...
```

## Skill Data Model

Database tables:

- `skills` (master metadata)
- `skill_conversations` (teaching chat sessions per skill)
- `skill_messages` (chat history within a skill conversation)

Relations:

- `skills -> skill_conversations` (`ON DELETE CASCADE`)
- `skill_conversations -> skill_messages` (`ON DELETE CASCADE`)

Implementation details:
- `POST /skills` creates a skill row with empty description and also creates one initial `skill_conversation`.
- Skill markdown path (`skill_md_path`) remains empty until publish.

## Backend API

Primary endpoints:

- `GET /skills`
- `POST /skills`
- `DELETE /skills/{skill_id}`
- `GET /skills/{skill_id}/markdown`
- `GET /skills/{skill_id}/conversations`
- `POST /skills/{skill_id}/conversations`
- `GET /skill-conversations/{skill_conversation_id}/messages`
- `POST /skill-conversations/{skill_conversation_id}/messages`
- `POST /skills/{skill_id}/publish`

Compatibility endpoints:

- `POST /agent/teach` (legacy quick-save)
- `GET /agent/skills` (legacy compatibility)

## UX Flow

`Teach the Agent` opens an almost full-window modal with:

- Left panel: existing skills list (hide/show available)
- Right panel:
  - skill markdown preview
  - skill teaching chat

Top-right controls:

- `+` create a new skill draft
- `🗑` delete selected skill
- `Show Skills` / `Hide Skills`

Behavior notes:
- Skill preview panel shows "not published yet" until `POST /skills/{skill_id}/publish` succeeds.
- Publish uses the selected skill conversation (or latest if none provided in API payload).

## Publish Behavior

Publishing a skill:

1. Reads selected skill conversation messages.
2. Uses skill agent to generate structured output:
   - `skill_name`
   - `description`
   - `skill_markdown`
3. Writes `SKILL.md` into shared volume.
4. Updates `skills` table metadata and `skill_md_path`.

The publish endpoint updates:
- `name`
- `description`
- `slug`
- `skill_md_path`
- `updated_at`

## Worker Consumption

Worker `code_executor_agent` can use:
- `search_agent_skills(query)` to find skills by keyword in id/frontmatter summary.
- `read_agent_skill(skill_name)` to load a selected shared skill.

Current retrieval is simple keyword matching over skill identifiers and frontmatter-derived summaries.

## Current Limitations

- Implementation is intentionally basic: only `SKILL.md` is generated.
- No automatic generation of code examples or multi-file skill package content yet.
- Skill retrieval is currently simplistic keyword matching (no semantic retrieval/RAG yet).

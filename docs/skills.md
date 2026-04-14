# Skills (Shared)

This document describes the current shared Skills implementation.

## Overview

Skills are reusable instructions learned through the `Teach the Agent` UI.

## Purpose

Skills are the app's reusable behavior feature: they let users teach domain/process guidance once and persist it as shared instructions that worker agents can apply in future tasks.

Key design decision:

- Skills are intended for worker agents (planner/executor).
- Main interface agent does not directly consume shared skills.

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

## Publish Behavior

Publishing a skill:

1. Reads selected skill conversation messages.
2. Uses skill agent to generate structured output:
   - `skill_name`
   - `description`
   - `skill_markdown`
3. Writes `SKILL.md` into shared volume.
4. Updates `skills` table metadata and `skill_md_path`.

## Current Limitations

- Implementation is intentionally basic: only `SKILL.md` is generated.
- No automatic generation of code examples or multi-file skill package content yet.
- Skill search is currently simplistic; a RAG-based retrieval layer likely makes more sense in future.

This is a good candidate for a future pull request.

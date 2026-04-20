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
- `skill_agent` (`gpt-5.4-mini`) orchestrates skill generation and can call only the worker code executor.

## Storage

Skills are stored in the shared Docker volume:

```text
/data/shared/skills/<skill_slug>/SKILL.md
```

Draft skills are created in an auxiliary shared directory and edited there until publish:

```text
/data/shared/skills_drafts/<draft_slug>/SKILL.md
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

The Skills UX is split into two entry points:

- `Teach the Agent`: draft creation and iterative teaching with the skill agent.
- `Skill Library`: published skills browsing and management.

### Teach the Agent (Drafts)

`Teach the Agent` opens an almost full-window editor with:

- Left panel: draft skills list.
- Center/right working area: draft `SKILL.md` preview and teaching chat.
- Top actions: create draft, rename, delete, and publish.

![Teach the Agent Draft UI](images/ux_teach_skills.png)

### Skill Library (Published)

`Skill Library` shows published skills only:

- Left panel: published skills list.
- Middle panel: `SKILL.md` content preview.
- Right panel: idle folder tree preview for the selected skill package.
- Actions include opening a published skill in draft mode for edits.

![Skill Library UI](images/ux_skills_library.png)

Top-right controls:

- `+` create a new skill draft
- `🗑` delete selected skill
- `Publish` publish selected draft

Behavior notes:
- Draft and published views are separated in the UI to avoid mixing editing and browsing contexts.
- Publish uses the selected skill conversation (or latest if none provided in API payload).

## Publish Behavior

Publishing a skill:

1. Reads selected skill conversation messages.
2. No agent is called during publish.
3. Backend validates the draft `SKILL.md` frontmatter (`name`, `description`).
4. Backend checks that no published skill with the same name/slug already exists.
5. Backend moves the full draft folder from `skills_drafts/` to `skills/`.
6. Backend updates `skills` table metadata and `skill_md_path`.

The publish endpoint updates:
- `name`
- `description`
- `slug`
- `skill_md_path`
- `updated_at`

## Worker Consumption

Worker `code_agent` can use:
- `search_agent_skills(query)` to find skills by keyword in id/frontmatter summary.
- `read_agent_skill(skill_name)` to load a selected shared skill.

Current retrieval is simple keyword matching over skill identifiers and frontmatter-derived summaries.

## Current Limitations

- Implementation is intentionally basic: only `SKILL.md` is generated.
- No automatic generation of code examples or multi-file skill package content yet.
- Skill retrieval is currently simplistic keyword matching (no semantic retrieval/RAG yet).

# Database And Storage

This document explains how the app stores reports, skills, and shared files.

## Overview

Persistence is split into two parts:

- PostgreSQL stores relational state for reports, skills, conversations, and messages.
- Docker volumes store PostgreSQL data and the shared report/skill filesystem used by backend and worker.

Main sources:

- SQL schema: `infra/postgres/app_schema.sql`
- Docker mounts: `docker-compose.yml`

## PostgreSQL Schema

The app database contains six main tables.

### Reports

`reports`

- `id BIGSERIAL PRIMARY KEY`
- `title TEXT NOT NULL`
- `created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()`

One row per report.

`conversations`

- `id BIGSERIAL PRIMARY KEY`
- `report_id BIGINT NOT NULL REFERENCES reports(id) ON DELETE CASCADE`
- `created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()`

One report can have many conversations.

`messages`

- `id BIGSERIAL PRIMARY KEY`
- `conversation_id BIGINT NOT NULL REFERENCES conversations(id) ON DELETE CASCADE`
- `role TEXT NOT NULL CHECK (role IN ('user', 'assistant'))`
- `content TEXT NOT NULL`
- `created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()`

One conversation can have many messages.

Relationship:

```text
reports
  -> conversations
    -> messages
```

Delete behavior:

- Deleting a report deletes its conversations.
- Deleting a conversation deletes its messages.

Indexes:

- `idx_conversations_report_id`
- `idx_messages_conversation_id`
- `idx_messages_created_at`

### Skills

`skills`

- `id BIGSERIAL PRIMARY KEY`
- `name TEXT NOT NULL`
- `description TEXT NOT NULL DEFAULT ''`
- `slug TEXT NOT NULL UNIQUE`
- `skill_md_path TEXT NOT NULL DEFAULT ''`
- `created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()`
- `updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()`

One row per skill draft or published skill record.

Important fields:

- `slug` is the stable filesystem-friendly identifier.
- `skill_md_path` points to the current `SKILL.md` file, either in drafts or published storage.

`skill_conversations`

- `id BIGSERIAL PRIMARY KEY`
- `skill_id BIGINT NOT NULL REFERENCES skills(id) ON DELETE CASCADE`
- `created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()`

One skill can have many teaching conversations.

`skill_messages`

- `id BIGSERIAL PRIMARY KEY`
- `skill_conversation_id BIGINT NOT NULL REFERENCES skill_conversations(id) ON DELETE CASCADE`
- `role TEXT NOT NULL CHECK (role IN ('user', 'assistant'))`
- `content TEXT NOT NULL`
- `created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()`

One skill conversation can have many messages.

Relationship:

```text
skills
  -> skill_conversations
    -> skill_messages
```

Delete behavior:

- Deleting a skill deletes its teaching conversations.
- Deleting a skill conversation deletes its messages.

Indexes:

- `idx_skill_conversations_skill_id`
- `idx_skill_messages_conversation_id`
- `idx_skill_messages_created_at`

## Seed Data

`infra/postgres/app_schema.sql` inserts a default report on first initialization:

- report title: `First Report`
- one initial conversation for that report

This happens only when the `reports` table is empty.

## Shared Filesystem

The backend and worker both mount the Docker volume `shared_data` at:

```text
/data/shared
```

This shared filesystem stores report workspaces and skill packages.

### Reports Workspace

Each report uses:

```text
/data/shared/jobs/report_<report_id>/
  report.md
  ...generated files
```

Typical contents:

- `report.md`
- generated charts under paths like `figures/...`
- analysis scripts or temporary artifacts created by the worker

The backend serves these files through:

- `/reports/{report_id}/markdown`
- `/reports/{report_id}/pdf`
- `/reports/{report_id}/files/{path}`

### Skills Workspace

Published skills live under:

```text
/data/shared/skills/<skill_slug>/SKILL.md
```

Draft skills live under:

```text
/data/shared/skills_drafts/<draft_slug>/SKILL.md
```

Current implementation may copy the full directory when opening a published skill in draft mode, so a skill package can contain more than only `SKILL.md`.

## Docker Volumes

From `docker-compose.yml`:

- `pg_data`
- `shared_data`

### `pg_data`

Mounted into Postgres at:

```text
/var/lib/postgresql/data
```

Purpose:

- persistent storage for the app PostgreSQL database

### `shared_data`

Mounted into backend and worker at:

```text
/data/shared
```

Purpose:

- shared report workspaces
- published skills
- skill drafts
- generated artifacts exchanged between backend and worker

## Operational Notes

- The relational source of truth for reports and skills is PostgreSQL.
- The file source of truth for report content is `report.md` in the shared volume.
- The file source of truth for a skill package is the `SKILL.md` path stored in `skills.skill_md_path`.
- Deleting a report or skill triggers best-effort filesystem cleanup in addition to DB deletion.
- Backend and worker both depend on the same `DATABASE_URL` and shared volume layout.

## Tradeoffs

- Persistence is split between PostgreSQL and the shared filesystem. This keeps the product model practical, but means the system does not live in a single storage layer.
- Reports and skills store metadata and conversation history in the database, while their actual file content lives on disk. That separation is useful for the product, but requires path management and best-effort filesystem cleanup.
- The current design favors simple, inspectable storage over stronger transactional guarantees between database state and filesystem state.

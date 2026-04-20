# Skills

This document is the product-level entry point for the Skills experience.

## What It Is

Skills are reusable instructions that users teach once and the worker can reuse later.

In product terms, a skill is a packaged piece of guidance such as:

- how to analyze a recurring business question
- how to structure a certain kind of report section
- how to handle domain-specific constraints or edge cases

Skills are not the main chat surface. They are reusable operational knowledge for future worker runs.

## Two User Entry Points

The Skills experience is intentionally split into two separate product modes:

- `Teach the Agent`
- `Skill Library`

This separation is important.

`Teach the Agent` is the editable draft workspace.

`Skill Library` is the published, browse-oriented workspace.

That split keeps experimentation and reuse separate.

## Teach the Agent

`Teach the Agent` is where users create and refine draft skills.

The modal is organized around:

- a left sidebar with draft skills
- a preview panel for the draft `SKILL.md`
- a working chat used to refine the draft

Inside this mode, a user can:

- create a new draft skill
- select an existing draft
- delete a draft
- open multiple conversations for the same draft
- iterate on the draft in chat
- publish the draft

The working chat is the main authoring surface. A good teaching loop is:

1. describe the goal of the skill
2. add constraints and expected behavior
3. add examples and edge cases
4. iterate until the draft instructions are usable
5. publish

![Teach the Agent Draft UI](images/ux_teach_skills.png)

## Skill Library

`Skill Library` is the browsing surface for published skills.

In this mode, a user can:

- browse published skills
- read the published `SKILL.md`
- inspect the skill package file tree
- open a published skill in draft mode to make changes

Published skills are treated as read-only in the UI. To modify one, the user opens it in draft and continues working there.

![Skill Library UI](images/ux_skills_library.png)

## Drafts vs Published Skills

This is the most important product distinction in the Skills feature.

Draft skills:

- are editable
- have a working chat
- can have multiple conversations
- are the place where iteration happens

Published skills:

- are meant for reuse, not direct editing
- are shown in the library view
- expose their package contents
- must be reopened in draft mode for changes

The workflow is therefore:

1. create or open a draft
2. refine it through teaching chat
3. publish it
4. reuse it later through the worker
5. if needed, reopen it as a draft and republish

## User Flow

### Create a Draft

Creating a skill immediately creates:

- a skill record
- an initial skill conversation
- a draft `SKILL.md`

This lets the user start iterating immediately.

### Teach Through Chat

The draft chat is where the user teaches the system what the skill should do.

Useful inputs include:

- the goal of the skill
- the intended use cases
- constraints and non-goals
- edge cases
- examples of good outputs

Each message continues refining the same draft workspace.

### Publish

Publishing is the step that turns a draft into a reusable shared skill.

At publish time:

- the draft package is moved into the published skills area
- the skill metadata is updated
- the skill becomes visible in `Skill Library`

The product intent is that publish is the moment where a private working draft becomes a reusable team asset.

### Edit a Published Skill

Published skills are not edited in place.

Instead, the user:

1. opens the skill in `Skill Library`
2. clicks `Open in Draft`
3. gets a new editable draft copy
4. makes changes there
5. publishes again

This preserves a cleaner separation between reusable assets and ongoing work.

## What The User Sees

In draft mode:

- the preview shows the current draft markdown
- the chat remains active
- `Publish` is available

In published mode:

- the preview shows the published markdown
- the file tree is visible
- the chat is hidden
- `Open in Draft` replaces editing actions

## What Gets Persisted

Skills persist in two forms:

- relational state in PostgreSQL
- files in the shared workspace

Database entities:

- `skills`
- `skill_conversations`
- `skill_messages`

Workspace layout:

```text
/data/shared/skills/<skill_slug>/SKILL.md
/data/shared/skills_drafts/<draft_slug>/SKILL.md
```

In product terms:

- the database stores the identity, metadata, and teaching history
- the shared filesystem stores the actual skill package
- draft and published skills live in different filesystem areas

## How Skills Are Consumed

Published skills are intended for the worker, not as direct chat personas for the main interface.

That means the product value of Skills is indirect but important:

- a user teaches a repeatable pattern once
- the worker can later discover and apply that skill in future tasks

This is why the Skills feature matters to the Reports experience even though it lives in a separate modal.

## Limitations

- The current product is centered on `SKILL.md`; richer multi-file packages are possible but not yet the main workflow.
- Skills are not yet organized into a more structured taxonomy. In the future, the library could introduce subcategories or other grouping mechanisms to make larger skill collections easier to navigate.
- Display titles edited in the UI are presentation-level labels, not a full persisted rename workflow.
- The app does not currently detect duplicate skills during skill creation, so users can create drafts that overlap in purpose or content.
- Skill retrieval is still simple; the worker does not use a more advanced retrieval layer yet.

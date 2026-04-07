# Agentic Analytics Reporting System

## Overview

An **agent-based analytics system** that converts natural language requests into **iteratively refined reports** using:

- LLM planning
- SQL generation + validation
- Python-based analysis & visualization
- Human-in-the-loop refinement
- Observability with Langfuse

## Core Idea

This is **not a one-shot system**.

It supports:
- report generation
- iterative refinement
- versioned outputs
- session-based workflows

## Architecture

```text
User -> UI -> Backend (LangGraph)
               |
               v
             Planner
               |
               v
          SQL Generator
               |
               v
           SQL Verifier
               |
               v
            DB Executor
               |
               v
        Artifact Worker (charts)
               |
               v
          Report Writer
```

## Components

### Frontend (Next.js)
- Two-pane UI:
  - left: report
  - right: session/chat

### Backend (FastAPI + LangGraph)
- orchestrates workflow
- manages sessions + iterations

### Artifact Worker
- generates charts/tables
- no DB access
- receives structured specs only

### Database (Postgres)
Stores:
- sessions
- messages
- report versions
- artifact metadata

### Storage
- shared volume for:
  - parquet data
  - generated artifacts

### Observability (Langfuse)
- traces workflow
- logs prompts, latency, tokens

## Iteration Model

User can refine reports.

Example:
1. "Generate sales report"
2. "Add breakdown by state"
3. "Focus on delayed deliveries"

System:
- updates plan
- reuses or recomputes data
- updates report

## Data Flow

SQL:
- executed only in backend
- validated before execution

Output:

```text
/shared/jobs/<job_id>/query_result.parquet
```

Artifacts:

```text
/shared/jobs/<job_id>/outputs/
```

## Safety

- read-only SQL
- schema-constrained queries
- worker isolated (no DB access)
- no arbitrary code execution

## Observability

Tracked steps:

```text
report_request
|-- plan
|-- generate_sql
|-- verify_sql
|-- execute_sql
|-- generate_artifacts
`-- write_report
```

## Evaluation

Metrics:
- SQL correctness
- report consistency
- revision success rate
- artifact correctness

## Docker Setup

Services:
- frontend
- backend
- artifact_worker
- postgres
- langfuse stack

Run:

```bash
docker compose -f docker-compose.yml -f docker-compose.langfuse.yml up
```

## Project Structure

```text
project/
|-- frontend/
|-- backend/
|-- worker/
|-- data/
|-- evals/
|-- docker-compose.yml
|-- docker-compose.langfuse.yml
`-- README.md
```

## Key Features

- agentic workflow (LangGraph)
- iterative report refinement
- SQL + Python tool use
- structured outputs
- observability (Langfuse)
- Dockerized system

## Future Work

- async jobs
- caching
- report diffing
- auth system
- advanced evals

## Summary

This project demonstrates a **production-style AI system** with:

- multi-step orchestration
- human-in-the-loop iteration
- safe tool usage
- observability and evaluation

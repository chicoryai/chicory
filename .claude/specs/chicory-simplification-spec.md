# Chicory Architecture Simplification - Technical Specification

## Overview

A comprehensive rewrite and simplification of the Chicory AI agent platform. The goal is to aggressively simplify the services architecture and technology stack while preserving the core value proposition: data connectivity, agent creation, and Claude-native experience.

**Core Philosophy**: Claude Agent SDK as the backbone for all agentic functionality.

## Success Criteria

- [ ] Eliminate LangChain/LangGraph entirely from the codebase
- [ ] Remove all dead code and unused dependencies
- [ ] Extract shared worker code to eliminate 90%+ duplication
- [ ] Implement dual authentication (local simple auth vs PropelAuth for cloud)
- [ ] Reduce Python dependency count by ~15 packages (revised after staff engineer review)
- [ ] Maintain all existing functionality for end users
- [ ] Maintain current 7 service separation (for scaling) but with cleaner code

## User Stories

### Chicory Core (Self-Hosted)
- As a developer, I want to run Chicory locally with simple email/password auth, so I don't need external auth providers
- As a developer, I want to connect my data warehouse and have it instantly queryable by agents
- As a developer, I want to create an agent in under a minute with just natural language instructions

### Chicory Cloud
- As an enterprise user, I want full SSO/RBAC via PropelAuth for organizational control
- As a team, we want shared projects with role-based access to agents and data sources
- As a compliance officer, I want audit logging of all agent actions

## Detailed Requirements

### 1. Technology Eliminations

#### 1.1 LangChain Ecosystem Removal
**Current State**: inference-worker uses LangChain (0.3.0), LangGraph, langchain-anthropic, langchain-mcp-adapters

**Files to Refactor/Delete**:
- `/services/inference-worker/services/training/workflows/data_understanding/hybrid_rag/adaptive_rag.py` (2048 lines)
- `/services/inference-worker/services/training/graphrag_config.py` (2593 lines)
- `/services/inference-worker/services/training/utils/preprocessing.py` (1878 lines)
- All `/workflows/` directories using LangGraph state machines

**Replacement Strategy**:
- Replace with Claude Agent SDK workflows
- Use simple async Python functions for data pipelines
- Remove GraphRAG complexity entirely (per user decision)

**Dependencies to Remove**:
- langchain (0.3.0)
- langchain-anthropic
- langchain-core
- langchain-openai
- langchain-mcp-adapters
- langgraph (0.2+)
- langsmith
- tiktoken (OpenAI tokenizer - not needed with Claude)

#### 1.2 Supabase Removal
**Current State**: `@supabase/supabase-js` in webapp package.json, `supabase.server.ts` file exists

**Finding**: DEAD CODE - not imported anywhere in webapp. Already using `chicory.server.ts` which calls backend-api.

**Action**:
- Delete `/services/webapp/app/utils/supabase.server.ts`
- Remove `@supabase/supabase-js` from package.json
- Remove SUPABASE_URL and SUPABASE_ANON_KEY from environment configs

#### 1.3 HTTP Client Consolidation
**Current State**: 3 different HTTP clients (requests, httpx, aiohttp)

**Action**: Standardize on `httpx` everywhere
- Replace `requests` calls with `httpx` (sync)
- Replace `aiohttp` calls with `httpx` (async)
- Single retry/timeout configuration pattern

**Files Affected**: ~35 files across services

#### 1.4 Document Processing (REVISED after Staff Engineer Review)
**Current State**: 8+ document processing libraries

**MUST KEEP** (Staff Engineer verified direct usage):
- `unstructured` (handles PDF, DOCX, PPTX, XLSX, HTML, MD, images)
- `pillow` (image processing)
- `pypdf` - **KEEP**: Used for PDF form filling (write/modify PDFs) in skills/processing-pdfs/scripts/ - unstructured cannot do this
- `lxml` - **KEEP**: Used for XML/DTD parsing in dtd2xml.py, schema_converter.py - unique functionality
- `chardet` - **KEEP**: Used for encoding detection in preprocessor.py
- `beautifulsoup4` - **KEEP**: Used in CustomBeautifulSoupTransformer in tools.py

**Safe to Remove**:
- `python-docx` - No imports found in codebase (only in requirements.txt)

### 2. Code Deduplication

#### 2.1 Worker Shared Package
**Problem**: inference-worker and training-worker share 90%+ identical code

**Solution**: Create `/packages/worker-common/` shared Python package

**Shared Code to Extract**:
- Database connector utilities
- S3/MinIO client wrappers
- RabbitMQ consumer base class
- Logging configuration
- Common utilities and helpers
- Task status management

**Keep Separate**:
- Task-specific handlers (data scanning vs agent execution)
- Worker entry points (for independent scaling)

#### 2.2 MCP Server Modularization
**Current State**: Monolithic files (db-mcp-server: 3179 lines, tools-mcp-server: 8154 lines)

**Action**: Break into provider plugins
```
services/db-mcp-server/
  server.py (entry point, <200 lines)
  providers/
    snowflake.py
    bigquery.py
    databricks.py
    postgresql.py
    mysql.py
```

```
services/tools-mcp-server/
  server.py (entry point, <200 lines)
  providers/
    looker.py
    dbt.py
    jira.py
    github.py
    redash.py
    airflow.py
```

### 3. Authentication Architecture

#### 3.1 Dual Auth System
**Runtime Configuration**: `AUTH_PROVIDER` environment variable

**Local Mode** (`AUTH_PROVIDER=local`):
- Simple email/password authentication
- Passwords hashed with bcrypt, stored in MongoDB
- JWT tokens for session management
- No external auth provider dependency

**Cloud Mode** (`AUTH_PROVIDER=propelauth`):
- Full PropelAuth integration (existing implementation)
- SSO, RBAC, organization management
- Audit logging

**Implementation**:
- Abstract auth interface in backend-api
- Provider implementations for local and propelauth
- Middleware that checks AUTH_PROVIDER and routes accordingly

### 4. Service Architecture (Preserved)

Keep current 7 services for independent scaling:

| Service | Purpose | Scaling |
|---------|---------|---------|
| webapp | React/Remix frontend | Horizontal |
| backend-api | REST API, coordination | Horizontal |
| agent-service | Claude SDK orchestration | Horizontal |
| db-mcp-server | Database tool exposure | Horizontal |
| tools-mcp-server | Integration tool exposure | Horizontal |
| data-worker (training-worker) | Data scanning, doc processing | Low (1-2) |
| agent-worker (inference-worker) | Agent task execution | High (many) |

### 5. Claude Agent SDK Integration

#### 5.1 Agent Service (Current - Keep)
- Already uses claude-agent-sdk (0.1.16)
- Manages workspaces, sessions, tool configurations
- Clean integration - preserve this

#### 5.2 Worker Claude Integration (New)
- Allow workers to use Claude Agent SDK for complex tasks
- Document understanding tasks can use Claude
- ProjectMD generation stays agent-driven

### 6. Infrastructure (Preserved)

Keep all 4 infrastructure services:
- MongoDB 7.0 - Primary data store
- Redis 7.2 - Caching, session management
- RabbitMQ 3.12 - Message queue for async tasks
- MinIO - S3-compatible object storage

### 7. Dependency Reduction Summary

**Python Packages to Remove** (~30+):
- langchain, langchain-core, langchain-anthropic, langchain-openai
- langgraph, langsmith
- tiktoken
- requests (replaced by httpx)
- aiohttp (replaced by httpx async)
- beautifulsoup4, lxml, chardet
- pypdf, python-docx (covered by unstructured)
- eralchemy, graphviz (GraphRAG-related)

**JavaScript Packages to Remove** (~3):
- @supabase/supabase-js and transitive deps

### 8. Entry Point Consolidation

**Current State**: 15+ main entry files across workers

**Target**: Single configurable entry point per worker
- `main.py` with environment-based configuration
- Remove: main_slack.py, main_pagerduty.py, main_litserve.py, managed.py
- Feature detection via environment variables

## Edge Cases & Error Handling

| Scenario | Expected Behavior |
|----------|-------------------|
| Local auth + no users exist | First user becomes admin |
| PropelAuth + misconfigured | Clear error message, service won't start |
| Missing Claude API key | Error at startup, not runtime |
| MCP server unavailable | Graceful degradation, agent continues without those tools |
| Worker crashes mid-task | Task stays in queue, another worker picks up |

## Out of Scope (This Iteration)

- Merging MCP servers (keeping separate for security)
- Frontend redesign (webapp stays as-is)
- Infrastructure consolidation (keep MongoDB, Redis, RabbitMQ, MinIO)
- Converting data scanning to agent-driven tasks
- Changing ProjectMD generation approach

## Future Iterations (Noted)

1. Consider merging backend-api and agent-service
2. Evaluate MCP server consolidation
3. Agent-driven data scanning
4. Frontend simplification

## Tradeoffs Accepted

1. **Keeping 7 services** vs aggressive merging: Chose scalability over simplicity
2. **Removing GraphRAG**: Losing advanced RAG capabilities for simplicity
3. **Dual auth complexity**: Worth it for local vs cloud flexibility
4. **Workers stay separate**: Code extraction over service merging

## Implementation Phases

### Phase 1: Quick Wins (Dead Code Removal)
1. Delete supabase.server.ts and remove dependency
2. Remove unused Python dependencies
3. Delete dead workflow files
4. Consolidate entry points

### Phase 2: LangChain Elimination
1. Audit all LangChain/LangGraph usage
2. Rewrite workflows using Claude Agent SDK
3. Remove LangChain dependencies
4. Test agent execution thoroughly

### Phase 3: Code Deduplication
1. Create worker-common package
2. Extract shared utilities
3. Refactor both workers to use shared package
4. Test both worker types

### Phase 4: MCP Modularization
1. Break db-mcp-server into provider modules
2. Break tools-mcp-server into provider modules
3. Test all integrations

### Phase 5: Authentication
1. Implement local auth provider
2. Create auth abstraction layer
3. Add runtime configuration
4. Test both auth modes

### Phase 6: HTTP Client Consolidation
1. Replace requests with httpx
2. Replace aiohttp with httpx async
3. Standardize retry/timeout patterns

## Verification Plan

### Unit Tests
- Auth provider switching
- Worker task routing
- MCP provider loading

### Integration Tests
- End-to-end agent execution with local auth
- Data source connection and scanning
- MCP tool invocation

### Manual Testing
- Create project with local auth
- Connect data source (Snowflake/BigQuery)
- Create and deploy agent
- Execute task and verify results
- Check audit trail (cloud mode)

---
Generated: 2026-02-01
Interview session for: Chicory architecture simplification and Claude Agent SDK backbone

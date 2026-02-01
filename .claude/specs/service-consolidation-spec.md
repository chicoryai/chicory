# Chicory Services Consolidation - Technical Specification

## Overview

Consolidate 6 separate Python services into 3 logical applications while maintaining independent scaling capabilities. The goal is to reduce operational complexity, infrastructure costs, and codebase duplication while improving developer experience and system performance.

### Current State: 6 Services
| Service | Purpose | Framework | Port |
|---------|---------|-----------|------|
| backend-api | Core API, project/agent management | FastAPI | 8000 |
| agent-service | Claude agent conversations | FastAPI + Claude CLI | 8083 |
| db-mcp-server | Database MCP operations | FastMCP | 8080 |
| tools-mcp-server | Tool/API MCP operations | FastMCP | 8080 |
| inference-worker | Inference job processing | FastAPI + RabbitMQ | 8000 |
| training-worker | Training/data scanning | RabbitMQ | N/A |

### Target State: 3 Applications
| Application | Contains | Deployment Modes |
|-------------|----------|------------------|
| **chicory-api** | backend-api + agent-service | Single HTTP server |
| **chicory-mcp** | db-mcp-server + tools-mcp-server | Single MCP server |
| **chicory-worker** | inference-worker + training-worker | Mode-based (inference/training/both) |

## Success Criteria

- [ ] All 6 services consolidated into 3 deployable applications
- [ ] Single Python 3.13+ codebase with shared core modules
- [ ] Local development requires only `docker-compose up` for all services
- [ ] Each application can be deployed independently with different scaling
- [ ] No Node.js dependency (Claude CLI migrated to Python SDK)
- [ ] API backward compatibility NOT required (breaking changes acceptable)
- [ ] Performance equal to or better than current architecture

## Detailed Requirements

### 1. Project Structure

```
chicory/
├── services/
│   ├── api/                          # Consolidated API application
│   │   ├── app/
│   │   │   ├── __init__.py
│   │   │   ├── main.py               # FastAPI entrypoint
│   │   │   ├── config.py             # API-specific config
│   │   │   ├── api/                   # HTTP routes
│   │   │   │   ├── v1/
│   │   │   │   │   ├── projects.py
│   │   │   │   │   ├── agents.py
│   │   │   │   │   ├── evaluations.py
│   │   │   │   │   ├── conversations.py  # From agent-service
│   │   │   │   │   └── ...
│   │   │   │   └── health.py
│   │   │   ├── services/              # Business logic
│   │   │   │   ├── project_service.py
│   │   │   │   ├── agent_service.py
│   │   │   │   ├── conversation_service.py  # Claude SDK integration
│   │   │   │   └── ...
│   │   │   └── models/                # Pydantic/Beanie models
│   │   ├── Dockerfile
│   │   ├── pyproject.toml
│   │   └── README.md
│   │
│   ├── mcp/                           # Consolidated MCP server
│   │   ├── app/
│   │   │   ├── __init__.py
│   │   │   ├── server.py              # FastMCP entrypoint
│   │   │   ├── config.py
│   │   │   ├── providers/             # All providers unified
│   │   │   │   ├── database/
│   │   │   │   │   ├── databricks.py
│   │   │   │   │   ├── snowflake.py
│   │   │   │   │   ├── bigquery.py
│   │   │   │   │   ├── redshift.py
│   │   │   │   │   └── glue.py
│   │   │   │   ├── tools/
│   │   │   │   │   ├── looker.py
│   │   │   │   │   ├── redash.py
│   │   │   │   │   ├── dbt.py
│   │   │   │   │   ├── jira.py
│   │   │   │   │   ├── s3.py
│   │   │   │   │   └── ...
│   │   │   │   └── base.py            # Provider base class
│   │   │   └── cache/                 # Connection caching
│   │   ├── Dockerfile
│   │   ├── pyproject.toml
│   │   └── README.md
│   │
│   └── worker/                        # Consolidated worker
│       ├── app/
│       │   ├── __init__.py
│       │   ├── main.py                # Worker entrypoint (mode-based)
│       │   ├── config.py
│       │   ├── consumer.py            # RabbitMQ consumer base
│       │   ├── handlers/
│       │   │   ├── inference/
│       │   │   │   ├── managed.py     # Inference job handler
│       │   │   │   ├── slack.py       # Slack integration
│       │   │   │   └── pagerduty.py   # PagerDuty integration
│       │   │   └── training/
│       │   │       ├── data_scan.py   # Data scanning jobs
│       │   │       ├── github.py
│       │   │       ├── confluence.py
│       │   │       └── ...
│       │   └── workflows/             # LangGraph workflows
│       ├── Dockerfile
│       ├── pyproject.toml
│       └── README.md
│
├── packages/
│   └── chicory-core/                  # Shared core library
│       ├── chicory_core/
│       │   ├── __init__.py
│       │   ├── config.py              # Base configuration
│       │   ├── database/
│       │   │   ├── mongodb.py         # Motor/Beanie setup
│       │   │   └── models.py          # Shared DB models
│       │   ├── queue/
│       │   │   ├── rabbitmq.py        # RabbitMQ client
│       │   │   └── publisher.py       # Job publishing
│       │   ├── cache/
│       │   │   └── redis.py           # Redis client
│       │   ├── auth/
│       │   │   └── credentials.py     # Credential management
│       │   ├── http/
│       │   │   └── client.py          # Shared HTTP client
│       │   └── observability/
│       │       ├── logging.py         # Structured logging
│       │       └── health.py          # Health check utilities
│       ├── pyproject.toml
│       └── README.md
│
├── docker-compose.yml                 # Local development
├── docker-compose.override.yml        # Local overrides
└── pyproject.toml                     # Workspace root
```

### 2. Configuration Strategy

Use a layered configuration approach for speed and efficiency:

```python
# packages/chicory-core/chicory_core/config.py
from pydantic_settings import BaseSettings
from functools import lru_cache

class CoreSettings(BaseSettings):
    """Base settings shared by all applications."""

    # Environment
    ENVIRONMENT: str = "development"
    LOG_LEVEL: str = "INFO"

    # MongoDB
    MONGODB_URI: str = "mongodb://localhost:27017"
    MONGODB_DATABASE: str = "chicory"

    # Redis
    REDIS_URL: str = "redis://localhost:6379"
    REDIS_CLUSTER_MODE: bool = False

    # RabbitMQ
    RABBITMQ_HOST: str = "localhost"
    RABBITMQ_PORT: int = 5672
    RABBITMQ_USERNAME: str = "guest"
    RABBITMQ_PASSWORD: str = "guest"
    RABBITMQ_SSL: bool = False

    # Inter-service communication
    API_BASE_URL: str = "http://localhost:8000"
    MCP_SERVER_URL: str = "http://localhost:8080"

    class Config:
        env_file = ".env"
        extra = "ignore"

@lru_cache()
def get_core_settings() -> CoreSettings:
    return CoreSettings()
```

Each application extends with mode-specific settings:

```python
# services/api/app/config.py
from chicory_core.config import CoreSettings

class APISettings(CoreSettings):
    """API-specific settings."""

    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    API_WORKERS: int = 4

    # Claude SDK
    ANTHROPIC_API_KEY: str = ""
    DEFAULT_MODEL: str = "claude-sonnet-4-5-20250929"

    # CORS
    CORS_ORIGINS: list[str] = ["*"]
```

### 3. Application Details

#### 3.1 chicory-api (Port 8000)

**Merges:** backend-api + agent-service

**Key Changes:**
- Agent-service functionality integrated as `/api/v1/conversations` routes
- Claude CLI dependency removed - uses `claude-agent-sdk` Python package directly
- Single FastAPI application with unified middleware

**Routes Structure:**
```
/health                          # Health check
/api/v1/projects/                # Project CRUD
/api/v1/agents/                  # Agent CRUD + execution
/api/v1/evaluations/             # Evaluation management
/api/v1/data-sources/            # Data source management
/api/v1/conversations/           # Agent conversations (from agent-service)
/api/v1/conversations/{id}/stream  # SSE streaming
```

**Claude SDK Migration:**
```python
# Before (agent-service with CLI)
result = subprocess.run(["claude", "--version"], capture_output=True)

# After (pure Python)
from anthropic import Anthropic
client = Anthropic()
response = client.messages.create(...)
```

#### 3.2 chicory-mcp (Port 8080)

**Merges:** db-mcp-server + tools-mcp-server

**Key Changes:**
- Single FastMCP server with unified provider registry
- Providers organized by category (database, tools)
- Shared connection caching across all providers
- Single credential fetching endpoint

**Provider Categories:**
```python
DATABASE_PROVIDERS = ["databricks", "snowflake", "bigquery", "redshift", "glue"]
TOOL_PROVIDERS = ["looker", "redash", "dbt", "datazone", "s3", "jira", "atlan", "azure_blob"]
```

**Unified MCP Tools:**
- All database query tools under `db_*` prefix
- All tool operations under `tool_*` prefix
- Automatic provider discovery based on credentials

#### 3.3 chicory-worker

**Merges:** inference-worker + training-worker

**Key Changes:**
- Single worker codebase with mode-based startup
- Shared RabbitMQ consumer infrastructure
- Unified job handling with routing by job type

**Deployment Modes:**
```bash
# Inference-only worker
WORKER_MODE=inference python -m app.main

# Training-only worker
WORKER_MODE=training python -m app.main

# Both (for local dev)
WORKER_MODE=all python -m app.main
```

**Queue Routing:**
```python
QUEUE_MAPPING = {
    "inference": ["inference_jobs", "slack_jobs", "pagerduty_jobs"],
    "training": ["training_jobs", "data_scan_jobs"],
}
```

### 4. Shared Core Library (chicory-core)

**Location:** `packages/chicory-core/`

**Consolidates:**
- MongoDB/Beanie initialization (currently duplicated in backend-api)
- RabbitMQ client (currently duplicated in workers)
- Redis client (currently in agent-service, inference-worker)
- Credential fetching (currently in MCP servers)
- HTTP client utilities
- Structured logging setup
- Health check utilities

**Installation:**
```toml
# Each service's pyproject.toml
[project]
dependencies = [
    "chicory-core @ file:../../packages/chicory-core",
]
```

### 5. Docker Configuration

**Base Image Strategy:**
```dockerfile
# All services use Python 3.13
FROM python:3.13-slim

# Common system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*
```

**docker-compose.yml (Local Development):**
```yaml
version: "3.8"

services:
  api:
    build: ./services/api
    ports:
      - "8000:8000"
    environment:
      - MONGODB_URI=mongodb://mongo:27017
      - REDIS_URL=redis://redis:6379
      - RABBITMQ_HOST=rabbitmq
    depends_on:
      - mongo
      - redis
      - rabbitmq

  mcp:
    build: ./services/mcp
    ports:
      - "8080:8080"
    environment:
      - API_BASE_URL=http://api:8000

  worker-inference:
    build: ./services/worker
    environment:
      - WORKER_MODE=inference
      - API_BASE_URL=http://api:8000
      - MCP_SERVER_URL=http://mcp:8080
    depends_on:
      - api
      - mcp
      - rabbitmq

  worker-training:
    build: ./services/worker
    environment:
      - WORKER_MODE=training
      - API_BASE_URL=http://api:8000
    depends_on:
      - api
      - rabbitmq

  # Infrastructure
  mongo:
    image: mongo:7
    ports:
      - "27017:27017"

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"

  rabbitmq:
    image: rabbitmq:3-management-alpine
    ports:
      - "5672:5672"
      - "15672:15672"
```

### 6. Migration Path

#### Phase 1: Create chicory-core Package
1. Extract shared utilities from all services
2. Create unified database, queue, cache clients
3. Add as dependency to all existing services (non-breaking)
4. Verify all services work with shared package

#### Phase 2: Consolidate MCP Servers
1. Create new `services/mcp/` structure
2. Port all providers from both MCP servers
3. Implement unified provider registry
4. Test with existing API
5. Deprecate old MCP servers

#### Phase 3: Consolidate Workers
1. Create new `services/worker/` structure
2. Port handlers from both workers
3. Implement mode-based startup
4. Test inference and training separately
5. Deprecate old workers

#### Phase 4: Consolidate API + Agent Service
1. Create new `services/api/` structure
2. Migrate Claude CLI to Python SDK
3. Port all routes from backend-api
4. Port conversation handling from agent-service
5. Test all endpoints
6. Deprecate old services

#### Phase 5: Cleanup
1. Remove deprecated service directories
2. Update CI/CD pipelines
3. Update infrastructure (deferred per user request)
4. Update documentation

### 7. Breaking Changes

| Area | Change | Migration Notes |
|------|--------|-----------------|
| Agent Service Port | 8083 → 8000 | Conversation routes now under `/api/v1/conversations` |
| MCP Server Ports | Separate 8080s → Single 8080 | Update service discovery |
| Environment Variables | Service-specific → Unified | See config section |
| Container Names | 6 containers → 3 containers | Update docker-compose references |

### 8. Performance Considerations

- **Connection Pooling:** Unified connection pools for MongoDB, Redis, RabbitMQ
- **Worker Concurrency:** Async handlers with configurable concurrency per mode
- **MCP Caching:** Shared connection cache with configurable TTL
- **API Response Time:** No expected degradation - reduced inter-service calls

### 9. Verification Plan

1. **Unit Tests:** Run existing tests (when added) against new structure
2. **Integration Tests:**
   - API: Test all endpoints via HTTP
   - MCP: Test all providers via MCP protocol
   - Workers: Test job processing via queue
3. **Local Development:** `docker-compose up` starts all services
4. **Load Testing:** Compare response times against current architecture
5. **End-to-End:** Create project → create agent → execute agent → view results

## Out of Scope (v1)

- Infrastructure (chicory-infra) Terraform changes - to be addressed separately
- Adding test coverage - deferred
- Performance benchmarking - deferred
- Observability improvements beyond current CloudWatch setup

## Open Questions

None remaining - all clarified during interview.

## Tradeoffs Accepted

| Decision | Tradeoff | Rationale |
|----------|----------|-----------|
| Python 3.13+ | May need dependency updates | Modern features, better performance |
| Merge agent-service into API | Coupling conversation logic with API | Eliminates Node.js dependency |
| Merge MCP servers | Larger single container | Simpler operations, shared caching |
| Mode-based workers | Same code, different configs | Unified codebase, independent scaling |
| Breaking API changes | Client updates needed | Cleaner architecture long-term |

---
Generated: 2026-02-01
Interview session for: Chicory services consolidation (agent-service, backend-api, db-mcp-server, inference-worker, tools-mcp-server, training-worker)

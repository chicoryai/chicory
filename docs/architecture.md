# Architecture Overview

Chicory is a microservices platform for building and running AI agents. This document explains how the components work together.

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              User Interface                                  │
│                                                                              │
│   ┌──────────────────────────────────────────────────────────────────────┐  │
│   │                         webapp (React/Remix)                          │  │
│   │                          http://localhost:3000                        │  │
│   └──────────────────────────────────────────────────────────────────────┘  │
└──────────────────────────────────┬──────────────────────────────────────────┘
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                              Core Services                                   │
│                                                                              │
│   ┌───────────────────┐   ┌───────────────────┐   ┌───────────────────┐    │
│   │   backend-api     │   │  agent-service    │   │  db-mcp-server    │    │
│   │    (FastAPI)      │◄──┤   (Claude SDK)    │──►│   (DB queries)    │    │
│   │   :8000           │   │                   │   │   :8080           │    │
│   └───────────────────┘   │                   │   └───────────────────┘    │
│            │              │                   │                             │
│            │              │                   │   ┌───────────────────┐    │
│            │              │                   │──►│ tools-mcp-server  │    │
│            │              │                   │   │ (Looker, Jira)    │    │
│            │              └───────────────────┘   │   :8080           │    │
│            │                       │              └───────────────────┘    │
│            │                       │                                        │
│            ▼                       ▼                                        │
│   ┌───────────────────┐   ┌───────────────────┐                            │
│   │ training-worker   │   │ inference-worker  │                            │
│   │  (ML training)    │   │  (ML inference)   │                            │
│   └───────────────────┘   └───────────────────┘                            │
└──────────────────────────────────┬──────────────────────────────────────────┘
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                            Infrastructure                                    │
│                                                                              │
│   ┌───────────────────┐   ┌───────────────────┐   ┌───────────────────┐    │
│   │     MongoDB       │   │      Redis        │   │    RabbitMQ       │    │
│   │   (Database)      │   │    (Cache)        │   │  (Message Queue)  │    │
│   │   :27017          │   │   :6379           │   │   :5672           │    │
│   └───────────────────┘   └───────────────────┘   └───────────────────┘    │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Service Descriptions

### Webapp

**Technology**: React, Remix, TypeScript

The web interface for Chicory. Users interact with this to:
- Create and manage projects
- Configure data source connections
- Build agents with natural language instructions
- Execute tasks and view results
- Create evaluations to test agent behavior

### Backend API

**Technology**: Python, FastAPI

The REST API that powers the webapp. Responsibilities:
- User authentication and authorization
- Project and agent CRUD operations
- Data source credential management
- Task execution coordination
- Evaluation management

### Agent Service

**Technology**: Python, Anthropic Claude SDK

The brain of Chicory. This service:
- Receives task execution requests from the backend
- Orchestrates Claude to execute agent instructions
- Coordinates with MCP servers for data access
- Manages tool calling and multi-step reasoning
- Returns structured results

### DB MCP Server

**Technology**: Python, MCP Protocol

Provides database connectivity to agents:
- Snowflake
- Databricks
- BigQuery
- PostgreSQL
- MySQL

Uses the [Model Context Protocol (MCP)](https://modelcontextprotocol.io/) to expose database operations as tools that Claude can call.

### Tools MCP Server

**Technology**: Python, MCP Protocol

Provides external tool integrations:
- Looker (dashboards, explores)
- dbt Cloud (models, runs)
- Jira (issues, projects)
- GitHub (repos, PRs)
- And more via MCP

### Training Worker

**Technology**: Python, ML libraries

Handles background ML training tasks:
- Document processing and indexing
- GraphRAG knowledge graph construction
- Embedding generation
- Custom model fine-tuning

### Inference Worker

**Technology**: Python, ML libraries

Handles ML inference for agentic workflows:
- Embedding retrieval
- Context augmentation
- Custom model inference

## Data Flow

### Task Execution

```
1. User creates task in webapp
         │
         ▼
2. Webapp calls backend-api
         │
         ▼
3. Backend queues task to RabbitMQ
         │
         ▼
4. Agent-service picks up task
         │
         ▼
5. Agent-service calls Claude API
         │
         ├──► Claude calls db-mcp-server for data
         │
         ├──► Claude calls tools-mcp-server for integrations
         │
         ▼
6. Agent-service returns result to backend
         │
         ▼
7. Backend stores result in MongoDB
         │
         ▼
8. Webapp displays result to user
```

### Training Pipeline

```
1. User uploads documents/connects data source
         │
         ▼
2. Backend queues training job to RabbitMQ
         │
         ▼
3. Training-worker processes documents
         │
         ├──► Extract text
         ├──► Generate embeddings
         ├──► Build knowledge graph
         │
         ▼
4. Training-worker stores results in MongoDB
         │
         ▼
5. Inference-worker can now use trained data
```

## Communication Patterns

### Synchronous (HTTP)

- Webapp → Backend API
- Backend API → Agent Service (for quick operations)
- Agent Service → MCP Servers

### Asynchronous (RabbitMQ)

- Backend API → Agent Service (for long-running tasks)
- Backend API → Training Worker
- Backend API → Inference Worker

### Caching (Redis)

- Session data
- API response caching
- Rate limiting counters
- Real-time status updates

### Persistence (MongoDB)

- User accounts
- Projects and agents
- Data source configurations
- Task history and results
- Training artifacts

## MCP Protocol

Chicory uses the [Model Context Protocol (MCP)](https://modelcontextprotocol.io/) for integrations. MCP provides a standardized way to:

1. **Expose tools** that Claude can call
2. **Provide context** from external systems
3. **Execute actions** in connected services

Example: When an agent needs to query Snowflake, the flow is:

```
Agent Service
     │
     ├── Calls Claude with task
     │
     ▼
Claude decides to use SQL tool
     │
     ├── Tool call: db-mcp-server/query_snowflake
     │
     ▼
DB MCP Server
     │
     ├── Executes query against Snowflake
     ├── Returns results to Claude
     │
     ▼
Claude processes results and continues
```

## Security Boundaries

### Credential Isolation

- **db-mcp-server**: Handles database credentials (most sensitive)
- **tools-mcp-server**: Handles OAuth tokens and API keys
- **agent-service**: Never sees raw credentials, only calls MCP servers

### Network Isolation

All services communicate over a private Docker network (`chicory-network`). Only these ports are exposed externally:

- `3000` (webapp)
- `8000` (backend-api)
- `15672` (RabbitMQ management UI, development only)

## Scaling Considerations

For production deployments:

| Component | Scaling Strategy |
|-----------|------------------|
| Webapp | Horizontal (stateless) |
| Backend API | Horizontal (stateless) |
| Agent Service | Horizontal (stateless) |
| MCP Servers | Horizontal (stateless) |
| Workers | Horizontal (via RabbitMQ) |
| MongoDB | Replica set or Atlas |
| Redis | Cluster or ElastiCache |
| RabbitMQ | Cluster or Amazon MQ |

## Next Steps

- [Installation Guide](installation.md) - Get Chicory running
- [Configuration Guide](configuration.md) - Customize your setup

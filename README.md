# Chicory

The open-source AI agent platform for data teams. Build, deploy, and manage AI agents that work with your data infrastructure.

## Quick Start

```bash
# Clone the repository
git clone https://github.com/chicoryai/chicory.git
cd chicory

# Install and start (requires Docker)
make install
```

That's it! Open http://localhost:3000 to get started.

## What is Chicory?

Chicory is a platform for building AI agents that understand your data stack. Connect to your databases (Snowflake, Databricks, BigQuery), tools (Looker, dbt, Jira), and let AI agents automate data workflows.

### Features

- **Agent Builder**: Create AI agents with natural language instructions
- **Data Source Connections**: Connect to Snowflake, Databricks, BigQuery, and more
- **Tool Integrations**: Looker, dbt Cloud, Jira, GitHub, and more via MCP
- **Evaluations**: Test and validate agent behavior before deployment
- **Full Platform**: Training, inference, and everything you need to run locally

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                         Chicory                             │
├─────────────────────────────────────────────────────────────┤
│  webapp (3000)     │  React/Remix frontend                  │
│  backend-api (8000)│  FastAPI REST API                      │
│  agent-service     │  Claude SDK integration                │
│  db-mcp-server     │  Database connections (MCP)            │
│  tools-mcp-server  │  External tool integrations (MCP)      │
│  training-worker   │  ML training (GraphRAG, indexing)      │
│  inference-worker  │  ML inference (agentic workflows)      │
├─────────────────────────────────────────────────────────────┤
│  MongoDB │ Redis │ RabbitMQ  (infrastructure)               │
└─────────────────────────────────────────────────────────────┘
```

## Requirements

- Docker Desktop (20.10+)
- 8GB RAM minimum (16GB recommended)
- Anthropic API key (for Claude)

## Commands

```bash
make install    # First-time setup
make start      # Start all services
make stop       # Stop all services
make dev        # Development mode with hot reload
make test       # Run all tests
make logs       # View logs
make status     # Check service health
make clean      # Remove containers and volumes
```

## Configuration

Copy `.env.example` to `.env` and configure:

```bash
# Required
ANTHROPIC_API_KEY=sk-ant-...

# Optional (for cloud storage)
AWS_ACCESS_KEY_ID=...
AWS_SECRET_ACCESS_KEY=...
S3_BUCKET=...
```

See [docs/configuration.md](docs/configuration.md) for all options.

## Documentation

- [Installation Guide](docs/installation.md)
- [Configuration](docs/configuration.md)
- [Architecture](docs/architecture.md)
- [FAQ](docs/faq.md)

## Chicory Cloud

Want managed infrastructure? [Chicory Cloud](https://app.chicory.ai) provides:
- Fully managed hosting
- Enterprise SSO
- Team collaboration
- Priority support

## Contributing

We welcome contributions! See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## License

Apache 2.0 - see [LICENSE](LICENSE) for details.

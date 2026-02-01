# Frequently Asked Questions

## General

### What is Chicory?

Chicory is an open-source platform for building AI agents that work with your data infrastructure. You can connect to databases (Snowflake, Databricks, BigQuery), tools (Looker, dbt, Jira), and create agents that automate data workflows.

### Is Chicory free?

Yes! Chicory is open source under the Apache 2.0 license. You can self-host it for free. The only cost is the Anthropic API usage for Claude.

### What's the difference between Chicory and Chicory Cloud?

| | Chicory (Open Source) | Chicory Cloud |
|---|---|---|
| Cost | Free (self-hosted) | Subscription |
| Hosting | You manage | Fully managed |
| Setup | `make install` | Sign up |
| Updates | Manual | Automatic |
| Support | Community | Priority |
| Enterprise features | No | Yes (SSO, audit logs) |

They are separate products. There's no migration path between them - you choose one based on your needs.

### How does Chicory compare to LangChain, AutoGPT, etc?

Chicory is specifically designed for **data teams** and **enterprise data infrastructure**. Key differences:

- **Native data connectors**: First-class support for Snowflake, Databricks, BigQuery
- **Tool integrations**: Built-in Looker, dbt, Jira support via MCP
- **Full platform**: UI, API, training pipeline, evaluations - not just a library
- **Production-ready**: Authentication, credential management, audit logging

## Installation

### What are the system requirements?

- Docker Desktop (version 20.10+)
- 8GB RAM minimum (16GB recommended)
- 10GB disk space
- Anthropic API key

### Can I run Chicory on Windows?

Yes, via Docker Desktop for Windows with WSL2 backend.

### Can I run Chicory on a remote server?

Yes. Any Linux server with Docker works. For production, we recommend:
- Ubuntu 22.04 LTS
- 16GB RAM or more
- SSD storage

### Why does installation take so long?

The first `make install` builds all Docker images, which can take 10-15 minutes. Subsequent starts are fast because images are cached.

### How do I update Chicory?

```bash
git pull
make build
make restart
```

## Configuration

### Do I need to configure everything in .env?

No. Only `ANTHROPIC_API_KEY` is required. Everything else has sensible defaults for local development.

### How do I connect to my own database instead of the built-in MongoDB?

Update these variables in `.env`:

```bash
MONGODB_URI=mongodb://user:pass@your-host:27017/chicory
```

Similarly for Redis and RabbitMQ if you want to use external services.

### Is my Anthropic API key stored securely?

Your API key is stored in your local `.env` file (which is gitignored) and passed to containers as environment variables. It's never stored in the database or transmitted anywhere except to Anthropic's API.

## Usage

### How do I create my first agent?

1. Open http://localhost:3000
2. Create a new project
3. Add a data source (or use the test connection)
4. Create an agent with natural language instructions
5. Execute a task to test it

See the [Getting Started guide](getting-started/) for detailed steps.

### What databases are supported?

- Snowflake
- Databricks
- BigQuery
- PostgreSQL
- MySQL
- And more via the MCP protocol

### What tools can agents use?

- Looker (dashboards, explores, queries)
- dbt Cloud (models, runs, documentation)
- Jira (issues, projects, comments)
- GitHub (repositories, PRs, issues)
- Custom tools via MCP

### Can I add custom tools?

Yes! Chicory uses the [Model Context Protocol (MCP)](https://modelcontextprotocol.io/). You can:
1. Write a custom MCP server
2. Add it to `docker-compose.yml`
3. Configure agents to use it

### How do evaluations work?

Evaluations let you test agent behavior:

1. Create test cases with expected outputs
2. Run the evaluation
3. Each test case is executed and compared to expectations
4. Results show pass/fail rates and areas for improvement

## Troubleshooting

### Services keep restarting

Check logs for specific errors:

```bash
make logs-backend-api
make logs-agent-service
```

Common causes:
- Out of memory (increase Docker memory allocation)
- Missing API key
- Port conflicts

### "Connection refused" errors

Wait for all services to become healthy:

```bash
make status
```

Services have health checks and may take 30-60 seconds to fully start.

### Tasks are stuck in "pending"

Check the agent service and RabbitMQ:

```bash
make logs-agent-service
make logs-rabbitmq
```

The agent service needs a valid Anthropic API key to process tasks.

### How do I reset everything?

```bash
make clean
make install
```

**Warning**: This deletes all data including projects, agents, and results.

## Security

### Is Chicory secure for production use?

For local development, the default configuration is fine. For production:

1. Generate strong passwords: `./scripts/generate-secrets.sh`
2. Use external managed databases with encryption
3. Run behind a reverse proxy with HTTPS
4. Set `DEBUG=false`

### Are database credentials encrypted?

Credentials are stored encrypted in MongoDB. The encryption key is derived from your `JWT_SECRET`.

### Can I use SSO?

The open-source version supports local authentication (email/password with JWT). For SSO, SAML, and enterprise authentication, see [Chicory Cloud](https://app.chicory.ai).

## Contributing

### How can I contribute?

See [CONTRIBUTING.md](../CONTRIBUTING.md) for guidelines. We welcome:
- Bug reports
- Feature requests
- Documentation improvements
- Code contributions

### Where do I report bugs?

Open an issue at [github.com/chicoryai/chicory/issues](https://github.com/chicoryai/chicory/issues).

### Is there a roadmap?

Check the GitHub issues and discussions for planned features and priorities.

## More Questions?

- [GitHub Issues](https://github.com/chicoryai/chicory/issues) - Bug reports and feature requests
- [GitHub Discussions](https://github.com/chicoryai/chicory/discussions) - Questions and community chat

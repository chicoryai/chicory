# Contributing to Chicory

Thank you for your interest in contributing to Chicory! This document provides guidelines for contributing to the project.

## Getting Started

1. Fork the repository
2. Clone your fork: `git clone https://github.com/YOUR_USERNAME/chicory.git`
3. Install and run locally: `make install`
4. Create a branch for your changes: `git checkout -b feature/your-feature-name`

## Development Setup

### Prerequisites

- Docker Desktop (20.10+)
- Git
- For Python services: Python 3.11+
- For webapp: Node.js 20+

### Running Locally

```bash
# Full stack
make install
make start

# Development mode (with hot reload)
make dev

# Run tests
make test
```

### Project Structure

```
chicory/
├── services/
│   ├── backend-api/       # FastAPI REST API (Python)
│   ├── webapp/            # React/Remix frontend (Node.js)
│   ├── agent-service/     # Claude SDK integration (Python)
│   ├── db-mcp-server/     # Database MCP server (Python)
│   ├── tools-mcp-server/  # Tools MCP server (Python)
│   ├── training-worker/   # ML training (Python)
│   └── inference-worker/  # ML inference (Python)
├── packages/
│   ├── python-common/     # Shared Python utilities
│   └── typescript-common/ # Shared TypeScript utilities
├── docs/                  # Documentation
├── e2e/                   # End-to-end tests
└── scripts/               # Helper scripts
```

## Making Changes

### Code Style

**Python:**
- Follow PEP 8
- Use type hints
- Format with `black`
- Lint with `ruff`

**TypeScript:**
- Follow the existing code style
- Use TypeScript strict mode
- Format with Prettier

### Commit Messages

Use clear, descriptive commit messages:
- `feat: add new data source connector for Postgres`
- `fix: resolve race condition in agent execution`
- `docs: update installation guide`
- `refactor: simplify authentication flow`

### Pull Requests

1. Update documentation if needed
2. Add tests for new functionality
3. Ensure all tests pass: `make test`
4. Create a PR with a clear description of your changes

## Testing

```bash
# Run all tests
make test

# Run specific test suites
make test-backend   # Python tests
make test-webapp    # TypeScript tests
make test-e2e       # End-to-end tests
```

## Reporting Issues

When reporting issues, please include:
- Chicory version (or commit hash)
- Steps to reproduce
- Expected vs actual behavior
- Relevant logs (`make logs`)

## Questions?

- Open an issue for questions about the codebase
- Check existing issues before creating new ones

## License

By contributing, you agree that your contributions will be licensed under the Apache 2.0 License.

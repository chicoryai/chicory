# Installation Guide

This guide covers installing and running Chicory on your local machine.

## Prerequisites

### Required

- **Docker Desktop** (version 20.10 or later)
  - [Download for Mac](https://docs.docker.com/desktop/install/mac-install/)
  - [Download for Windows](https://docs.docker.com/desktop/install/windows-install/)
  - [Download for Linux](https://docs.docker.com/desktop/install/linux-install/)

- **Anthropic API Key**
  - Sign up at [console.anthropic.com](https://console.anthropic.com)
  - Create an API key

### Recommended

- **8GB RAM minimum** (16GB recommended for running all services)
- **10GB disk space** for Docker images and data

## Quick Install

The fastest way to get started:

```bash
# Clone the repository
git clone https://github.com/chicoryai/chicory.git
cd chicory

# Install and start
make install
```

The installer will:
1. Check that Docker is running
2. Generate secure random credentials for MongoDB, Redis, and RabbitMQ
3. Prompt you for your Anthropic API key
4. Build all Docker images
5. Start all services
6. Run health checks

Once complete, open [http://localhost:3000](http://localhost:3000) to access the webapp.

## Manual Installation

If you prefer to configure things manually:

### 1. Clone the Repository

```bash
git clone https://github.com/chicoryai/chicory.git
cd chicory
```

### 2. Create Environment File

```bash
cp .env.example .env
```

### 3. Configure Required Settings

Edit `.env` and set your Anthropic API key:

```bash
ANTHROPIC_API_KEY=sk-ant-your-key-here
```

### 4. Generate Secure Credentials (Recommended)

```bash
./scripts/generate-secrets.sh
```

This generates random passwords for MongoDB, Redis, and RabbitMQ.

### 5. Build and Start

```bash
# Build all Docker images
make build

# Start all services
make start
```

### 6. Verify Installation

```bash
make status
```

All services should show as "healthy".

## Service Ports

Once running, these services are available:

| Service | URL | Description |
|---------|-----|-------------|
| Webapp | http://localhost:3000 | Web interface |
| Backend API | http://localhost:8000 | REST API |
| API Docs | http://localhost:8000/docs | OpenAPI documentation |
| MongoDB | localhost:27017 | Database (internal) |
| Redis | localhost:6379 | Cache (internal) |
| RabbitMQ | localhost:5672 | Message queue (internal) |
| RabbitMQ UI | http://localhost:15672 | Queue management UI |

## Development Mode

For development with hot reload:

```bash
make dev
```

This mounts local source directories into containers and enables automatic reload when files change.

## Troubleshooting

### Docker Not Running

```
Error: Docker is not running
```

Start Docker Desktop and try again.

### Port Already in Use

```
Error: port 3000 already allocated
```

Stop the conflicting service or change the port in `docker-compose.yml`.

### Services Not Starting

Check logs for specific errors:

```bash
# All logs
make logs

# Specific service
make logs-backend-api
make logs-webapp
```

### Out of Memory

If services are crashing, Docker may need more memory. In Docker Desktop settings, increase the memory allocation to at least 8GB.

### Reset Everything

To completely reset and start fresh:

```bash
make clean
make install
```

**Warning**: This removes all data including MongoDB databases.

## Updating

To update to the latest version:

```bash
git pull
make build
make restart
```

## Uninstalling

To remove Chicory and all its data:

```bash
make clean
docker rmi $(docker images 'chicory*' -q) 2>/dev/null || true
```

## Next Steps

- [Configuration Guide](configuration.md) - Customize your installation
- [Architecture Overview](architecture.md) - Understand how Chicory works
- [Getting Started](getting-started/) - Create your first agent

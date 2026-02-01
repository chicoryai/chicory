# Chicory Makefile
# Single-command operations for the Chicory platform

.PHONY: help install start stop restart dev test test-backend test-webapp test-e2e build clean logs status

# Default target
help:
	@echo "Chicory Platform - Available Commands"
	@echo "======================================"
	@echo ""
	@echo "Getting Started:"
	@echo "  make install       First-time setup (generates secrets, builds, starts)"
	@echo ""
	@echo "Running:"
	@echo "  make start         Start all services"
	@echo "  make stop          Stop all services"
	@echo "  make restart       Full restart"
	@echo "  make dev           Development mode with hot reload"
	@echo ""
	@echo "Testing:"
	@echo "  make test          Run all tests"
	@echo "  make test-backend  Run Python tests only"
	@echo "  make test-webapp   Run TypeScript tests only"
	@echo "  make test-e2e      Run end-to-end tests"
	@echo ""
	@echo "Building:"
	@echo "  make build         Build all Docker images"
	@echo ""
	@echo "Monitoring:"
	@echo "  make logs          View all service logs"
	@echo "  make logs-backend  View backend-api logs"
	@echo "  make logs-webapp   View webapp logs"
	@echo "  make status        Health check all services"
	@echo ""
	@echo "Cleanup:"
	@echo "  make clean         Remove containers and volumes"
	@echo ""

# =============================================================================
# Installation
# =============================================================================

install: check-docker generate-env generate-secrets build start wait-healthy
	@echo ""
	@echo "=============================================="
	@echo "  Chicory installation complete!"
	@echo "=============================================="
	@echo ""
	@echo "  Web UI:     http://localhost:3000"
	@echo "  API:        http://localhost:8000"
	@echo "  RabbitMQ:   http://localhost:15672"
	@echo ""
	@echo "  Run 'make logs' to view service logs"
	@echo "  Run 'make status' to check service health"
	@echo ""

install-interactive:
	@./scripts/install.sh --interactive

# =============================================================================
# Running Services
# =============================================================================

start: check-docker check-env
	@echo "Starting Chicory services..."
	@docker compose up -d
	@echo "Services started. Run 'make status' to check health."

stop:
	@echo "Stopping Chicory services..."
	@docker compose down
	@echo "Services stopped."

restart: stop start

dev: check-docker check-env
	@echo "Starting Chicory in development mode..."
	@docker compose -f docker-compose.yml -f docker-compose.dev.yml up

# =============================================================================
# Testing
# =============================================================================

test: test-backend test-webapp

test-backend:
	@echo "Running backend tests..."
	@docker compose run --rm backend-api pytest -v

test-webapp:
	@echo "Running webapp tests..."
	@docker compose run --rm webapp yarn test

test-e2e: start wait-healthy
	@echo "Running end-to-end tests..."
	@docker compose run --rm e2e npx playwright test

# =============================================================================
# Building
# =============================================================================

build:
	@echo "Building Docker images..."
	@docker compose build
	@echo "Build complete."

build-no-cache:
	@echo "Building Docker images (no cache)..."
	@docker compose build --no-cache
	@echo "Build complete."

# =============================================================================
# Monitoring
# =============================================================================

logs:
	@docker compose logs -f

logs-backend:
	@docker compose logs -f backend-api

logs-webapp:
	@docker compose logs -f webapp

logs-agent:
	@docker compose logs -f agent-service

logs-mcp:
	@docker compose logs -f db-mcp-server tools-mcp-server

logs-workers:
	@docker compose logs -f training-worker inference-worker

status:
	@./scripts/health-check.sh

# =============================================================================
# Cleanup
# =============================================================================

clean:
	@echo "Removing containers and volumes..."
	@docker compose down -v --remove-orphans
	@echo "Cleanup complete."

clean-all: clean
	@echo "Removing Docker images..."
	@docker compose down --rmi local
	@echo "Full cleanup complete."

# =============================================================================
# Helpers
# =============================================================================

check-docker:
	@command -v docker >/dev/null 2>&1 || { echo "Error: Docker is not installed. Please install Docker Desktop."; exit 1; }
	@docker info >/dev/null 2>&1 || { echo "Error: Docker is not running. Please start Docker Desktop."; exit 1; }

check-env:
	@test -f .env || { echo "Error: .env file not found. Run 'make install' first."; exit 1; }

generate-env:
	@if [ ! -f .env ]; then \
		echo "Creating .env from template..."; \
		cp .env.example .env; \
		echo ".env file created. Please edit it to add your ANTHROPIC_API_KEY."; \
	else \
		echo ".env file already exists."; \
	fi

generate-secrets:
	@./scripts/generate-secrets.sh

wait-healthy:
	@echo "Waiting for services to be healthy..."
	@./scripts/health-check.sh --wait

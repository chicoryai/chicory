#!/bin/bash
# Health check script for Chicory services
# Checks that all services are running and healthy

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Configuration
WAIT_MODE=false
MAX_WAIT=120  # seconds
CHECK_INTERVAL=5  # seconds

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --wait|-w)
            WAIT_MODE=true
            shift
            ;;
        --timeout|-t)
            MAX_WAIT=$2
            shift 2
            ;;
        *)
            shift
            ;;
    esac
done

# Check if a service is healthy
check_service() {
    local service=$1
    local port=$2
    local path=${3:-/}

    if curl -s -o /dev/null -w "%{http_code}" "http://localhost:$port$path" | grep -q "200\|301\|302\|404"; then
        return 0
    fi
    return 1
}

# Check if a container is running
check_container() {
    local container=$1
    docker compose ps --format json 2>/dev/null | grep -q "\"$container\".*running" 2>/dev/null
}

# Print status
print_status() {
    local name=$1
    local status=$2
    local details=${3:-""}

    if [ "$status" = "healthy" ]; then
        echo -e "  ${GREEN}✓${NC} $name ${details}"
    elif [ "$status" = "starting" ]; then
        echo -e "  ${YELLOW}○${NC} $name ${details}"
    else
        echo -e "  ${RED}✗${NC} $name ${details}"
    fi
}

# Main health check
run_health_check() {
    cd "$ROOT_DIR"

    echo ""
    echo "Chicory Service Status"
    echo "======================"
    echo ""

    local all_healthy=true

    # Infrastructure services
    echo "Infrastructure:"

    # MongoDB
    if docker compose exec -T mongodb mongosh --eval "db.adminCommand('ping')" &>/dev/null; then
        print_status "MongoDB" "healthy" "(27017)"
    else
        print_status "MongoDB" "unhealthy" "(27017)"
        all_healthy=false
    fi

    # Redis
    if docker compose exec -T redis redis-cli ping &>/dev/null; then
        print_status "Redis" "healthy" "(6379)"
    else
        print_status "Redis" "unhealthy" "(6379)"
        all_healthy=false
    fi

    # RabbitMQ
    if check_service "rabbitmq" 15672 "/"; then
        print_status "RabbitMQ" "healthy" "(5672, 15672)"
    else
        print_status "RabbitMQ" "unhealthy" "(5672, 15672)"
        all_healthy=false
    fi

    echo ""
    echo "Application Services:"

    # Backend API
    if check_service "backend-api" 8000 "/health"; then
        print_status "Backend API" "healthy" "(8000)"
    else
        print_status "Backend API" "unhealthy" "(8000)"
        all_healthy=false
    fi

    # Webapp
    if check_service "webapp" 3000 "/"; then
        print_status "Webapp" "healthy" "(3000)"
    else
        print_status "Webapp" "unhealthy" "(3000)"
        all_healthy=false
    fi

    # Agent Service
    if check_service "agent-service" 8083 "/health"; then
        print_status "Agent Service" "healthy" "(8083)"
    else
        print_status "Agent Service" "unhealthy" "(8083)"
        all_healthy=false
    fi

    # DB MCP Server
    if check_service "db-mcp-server" 8081 "/health"; then
        print_status "DB MCP Server" "healthy" "(8081)"
    else
        print_status "DB MCP Server" "unhealthy" "(8081)"
        all_healthy=false
    fi

    # Tools MCP Server
    if check_service "tools-mcp-server" 8082 "/health"; then
        print_status "Tools MCP Server" "healthy" "(8082)"
    else
        print_status "Tools MCP Server" "unhealthy" "(8082)"
        all_healthy=false
    fi

    echo ""
    echo "ML Workers:"

    # Training Worker (check container running, not HTTP)
    if docker compose ps training-worker 2>/dev/null | grep -q "running"; then
        print_status "Training Worker" "healthy" "(running)"
    else
        print_status "Training Worker" "unhealthy" "(not running)"
        all_healthy=false
    fi

    # Inference Worker (check container running, not HTTP)
    if docker compose ps inference-worker 2>/dev/null | grep -q "running"; then
        print_status "Inference Worker" "healthy" "(running)"
    else
        print_status "Inference Worker" "unhealthy" "(not running)"
        all_healthy=false
    fi

    echo ""

    if [ "$all_healthy" = true ]; then
        echo -e "${GREEN}All services are healthy!${NC}"
        return 0
    else
        echo -e "${YELLOW}Some services are not healthy.${NC}"
        return 1
    fi
}

# Wait for services to be healthy
wait_for_healthy() {
    local start_time=$(date +%s)
    local elapsed=0

    echo "Waiting for services to be healthy (timeout: ${MAX_WAIT}s)..."
    echo ""

    while [ $elapsed -lt $MAX_WAIT ]; do
        if run_health_check 2>/dev/null; then
            return 0
        fi

        elapsed=$(($(date +%s) - start_time))
        remaining=$((MAX_WAIT - elapsed))

        if [ $remaining -gt 0 ]; then
            echo ""
            echo "Retrying in ${CHECK_INTERVAL}s... (${remaining}s remaining)"
            sleep $CHECK_INTERVAL
        fi
    done

    echo ""
    echo -e "${RED}Timeout waiting for services to be healthy.${NC}"
    echo "Run 'make logs' to see service logs for debugging."
    return 1
}

# Main
if [ "$WAIT_MODE" = true ]; then
    wait_for_healthy
else
    run_health_check
fi

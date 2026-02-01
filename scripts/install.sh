#!/bin/bash
# Chicory Installation Script
# One-command setup for the Chicory platform

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_header() {
    echo ""
    echo -e "${BLUE}=============================================="
    echo "  Chicory Platform Installation"
    echo -e "==============================================${NC}"
    echo ""
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}! $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

# Check prerequisites
check_prerequisites() {
    echo "Checking prerequisites..."

    # Check Docker
    if ! command -v docker &> /dev/null; then
        print_error "Docker is not installed."
        echo "Please install Docker Desktop from: https://docs.docker.com/get-docker/"
        exit 1
    fi
    print_success "Docker is installed"

    # Check Docker is running
    if ! docker info &> /dev/null; then
        print_error "Docker is not running."
        echo "Please start Docker Desktop and try again."
        exit 1
    fi
    print_success "Docker is running"

    # Check available memory (recommend 8GB)
    if command -v docker &> /dev/null; then
        DOCKER_MEM=$(docker info 2>/dev/null | grep "Total Memory" | awk '{print $3}' | sed 's/GiB//')
        if [ -n "$DOCKER_MEM" ]; then
            if (( $(echo "$DOCKER_MEM < 8" | bc -l 2>/dev/null || echo "0") )); then
                print_warning "Docker has less than 8GB RAM. Some services may be slow."
            fi
        fi
    fi

    echo ""
}

# Setup environment
setup_environment() {
    echo "Setting up environment..."

    cd "$ROOT_DIR"

    if [ -f .env ]; then
        print_warning ".env file already exists. Keeping existing configuration."
    else
        cp .env.example .env
        print_success "Created .env file from template"
    fi

    # Check for Anthropic API key
    if grep -q "^ANTHROPIC_API_KEY=$" .env 2>/dev/null; then
        echo ""
        echo -e "${YELLOW}ANTHROPIC_API_KEY is not set.${NC}"
        echo "You need an Anthropic API key to use Chicory."
        echo "Get one at: https://console.anthropic.com/"
        echo ""

        if [ "$INTERACTIVE" = true ]; then
            read -p "Enter your Anthropic API key (or press Enter to skip): " API_KEY
            if [ -n "$API_KEY" ]; then
                sed -i.bak "s/^ANTHROPIC_API_KEY=$/ANTHROPIC_API_KEY=$API_KEY/" .env
                rm -f .env.bak
                print_success "API key configured"
            else
                print_warning "Skipping API key. Edit .env later to add it."
            fi
        else
            print_warning "Please edit .env to add your ANTHROPIC_API_KEY"
        fi
    else
        print_success "ANTHROPIC_API_KEY is configured"
    fi

    echo ""
}

# Generate secrets
generate_secrets() {
    echo "Generating secrets..."
    "$SCRIPT_DIR/generate-secrets.sh"
    echo ""
}

# Build images
build_images() {
    echo "Building Docker images..."
    echo "This may take a few minutes on first run."
    echo ""

    cd "$ROOT_DIR"
    docker compose build

    print_success "Docker images built"
    echo ""
}

# Start services
start_services() {
    echo "Starting services..."

    cd "$ROOT_DIR"
    docker compose up -d

    print_success "Services started"
    echo ""
}

# Wait for health
wait_for_health() {
    echo "Waiting for services to be healthy..."
    "$SCRIPT_DIR/health-check.sh" --wait
    echo ""
}

# Print success
print_completion() {
    echo -e "${GREEN}=============================================="
    echo "  Installation Complete!"
    echo -e "==============================================${NC}"
    echo ""
    echo "  Web UI:        http://localhost:3000"
    echo "  API:           http://localhost:8000"
    echo "  RabbitMQ UI:   http://localhost:15672"
    echo ""
    echo "  Useful commands:"
    echo "    make logs     - View service logs"
    echo "    make status   - Check service health"
    echo "    make stop     - Stop all services"
    echo "    make restart  - Restart all services"
    echo ""
}

# Main
main() {
    INTERACTIVE=false

    # Parse arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            --interactive|-i)
                INTERACTIVE=true
                shift
                ;;
            *)
                shift
                ;;
        esac
    done

    print_header
    check_prerequisites
    setup_environment
    generate_secrets
    build_images
    start_services
    wait_for_health
    print_completion
}

main "$@"

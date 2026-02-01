#!/bin/bash
# Generate random secrets for Chicory services
# This script creates secure random passwords for MongoDB, Redis, and RabbitMQ

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"
ENV_FILE="$ROOT_DIR/.env"
SECRETS_FILE="$ROOT_DIR/.env.secrets"

# Generate a random password
generate_password() {
    # Generate 24-character alphanumeric password
    if command -v openssl &> /dev/null; then
        openssl rand -base64 32 | tr -dc 'a-zA-Z0-9' | head -c 24
    else
        # Fallback for systems without openssl
        cat /dev/urandom | tr -dc 'a-zA-Z0-9' | head -c 24
    fi
}

# Generate JWT secret (longer for security)
generate_jwt_secret() {
    if command -v openssl &> /dev/null; then
        openssl rand -base64 64 | tr -d '\n'
    else
        cat /dev/urandom | tr -dc 'a-zA-Z0-9' | head -c 64
    fi
}

echo "Checking secrets..."

# Check if .env exists
if [ ! -f "$ENV_FILE" ]; then
    echo "Error: .env file not found. Run 'make install' first."
    exit 1
fi

# Check if secrets are already set (not default values)
MONGO_PASS=$(grep "^MONGO_PASSWORD=" "$ENV_FILE" | cut -d'=' -f2)
REDIS_PASS=$(grep "^REDIS_PASSWORD=" "$ENV_FILE" | cut -d'=' -f2)
RABBITMQ_PASS=$(grep "^RABBITMQ_PASSWORD=" "$ENV_FILE" | cut -d'=' -f2)

# Only generate if using default passwords
if [ "$MONGO_PASS" = "chicory" ] && [ "$REDIS_PASS" = "chicory" ] && [ "$RABBITMQ_PASS" = "chicory" ]; then
    echo "Generating secure random passwords..."

    NEW_MONGO_PASS=$(generate_password)
    NEW_REDIS_PASS=$(generate_password)
    NEW_RABBITMQ_PASS=$(generate_password)
    NEW_JWT_SECRET=$(generate_jwt_secret)

    # Update .env file
    if [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS
        sed -i '' "s/^MONGO_PASSWORD=chicory$/MONGO_PASSWORD=$NEW_MONGO_PASS/" "$ENV_FILE"
        sed -i '' "s/^REDIS_PASSWORD=chicory$/REDIS_PASSWORD=$NEW_REDIS_PASS/" "$ENV_FILE"
        sed -i '' "s/^RABBITMQ_PASSWORD=chicory$/RABBITMQ_PASSWORD=$NEW_RABBITMQ_PASS/" "$ENV_FILE"
        sed -i '' "s|mongodb://admin:chicory@|mongodb://admin:$NEW_MONGO_PASS@|" "$ENV_FILE"
        sed -i '' "s|redis://:chicory@|redis://:$NEW_REDIS_PASS@|" "$ENV_FILE"
        sed -i '' "s|amqp://admin:chicory@|amqp://admin:$NEW_RABBITMQ_PASS@|" "$ENV_FILE"
    else
        # Linux
        sed -i "s/^MONGO_PASSWORD=chicory$/MONGO_PASSWORD=$NEW_MONGO_PASS/" "$ENV_FILE"
        sed -i "s/^REDIS_PASSWORD=chicory$/REDIS_PASSWORD=$NEW_REDIS_PASS/" "$ENV_FILE"
        sed -i "s/^RABBITMQ_PASSWORD=chicory$/RABBITMQ_PASSWORD=$NEW_RABBITMQ_PASS/" "$ENV_FILE"
        sed -i "s|mongodb://admin:chicory@|mongodb://admin:$NEW_MONGO_PASS@|" "$ENV_FILE"
        sed -i "s|redis://:chicory@|redis://:$NEW_REDIS_PASS@|" "$ENV_FILE"
        sed -i "s|amqp://admin:chicory@|amqp://admin:$NEW_RABBITMQ_PASS@|" "$ENV_FILE"
    fi

    # Add JWT secret if not present
    if ! grep -q "^JWT_SECRET=" "$ENV_FILE"; then
        echo "" >> "$ENV_FILE"
        echo "# JWT Secret (auto-generated)" >> "$ENV_FILE"
        echo "JWT_SECRET=$NEW_JWT_SECRET" >> "$ENV_FILE"
    fi

    echo "✓ Secure passwords generated"
else
    echo "✓ Custom passwords already configured"
fi

# Configuration Guide

Chicory is configured through environment variables in the `.env` file. This guide documents all available options.

## Quick Start

```bash
# Copy the example configuration
cp .env.example .env

# Generate secure credentials
./scripts/generate-secrets.sh

# Edit to add your API key
vim .env  # or your preferred editor
```

## Required Configuration

### Anthropic API Key

```bash
ANTHROPIC_API_KEY=sk-ant-your-key-here
```

This is the only required configuration. Get your API key at [console.anthropic.com](https://console.anthropic.com).

## Optional Configuration

### OpenAI API Key

```bash
OPENAI_API_KEY=sk-your-openai-key
```

Optional. Used for additional inference capabilities.

### MongoDB

```bash
MONGO_USER=admin
MONGO_PASSWORD=your-secure-password
MONGO_HOST=mongodb
MONGO_PORT=27017
MONGO_DATABASE=chicory
```

Default credentials work for local development. **Change passwords for production.**

### Redis

```bash
REDIS_PASSWORD=your-secure-password
REDIS_HOST=redis
REDIS_PORT=6379
```

### RabbitMQ

```bash
RABBITMQ_USER=admin
RABBITMQ_PASSWORD=your-secure-password
RABBITMQ_HOST=rabbitmq
RABBITMQ_PORT=5672
```

### AWS / S3 Storage

Optional. Configure for cloud file storage instead of local storage.

```bash
AWS_ACCESS_KEY_ID=AKIA...
AWS_SECRET_ACCESS_KEY=your-secret-key
AWS_DEFAULT_REGION=us-west-2
S3_BUCKET=your-bucket-name
```

### Debug Mode

```bash
DEBUG=true
LOG_LEVEL=DEBUG
```

Enable for verbose logging. Options: `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`.

### JWT Authentication

```bash
JWT_SECRET=your-secure-random-string
JWT_ALGORITHM=HS256
JWT_EXPIRY_HOURS=24
```

The JWT secret should be a long random string. Generate one with:

```bash
openssl rand -hex 32
```

## Environment-Specific Configuration

### Development

The default configuration in `.env.example` is optimized for local development:
- Debug mode enabled
- Default credentials for local services
- Hot reload enabled in `docker-compose.dev.yml`

### Production

For production deployments:

1. **Generate strong passwords**:
   ```bash
   ./scripts/generate-secrets.sh
   ```

2. **Disable debug mode**:
   ```bash
   DEBUG=false
   LOG_LEVEL=INFO
   ```

3. **Use external managed databases** (recommended):
   - MongoDB Atlas or DocumentDB
   - ElastiCache for Redis
   - Amazon MQ for RabbitMQ

4. **Enable S3 storage**:
   ```bash
   AWS_ACCESS_KEY_ID=...
   AWS_SECRET_ACCESS_KEY=...
   S3_BUCKET=your-bucket
   ```

5. **Set a strong JWT secret**:
   ```bash
   JWT_SECRET=$(openssl rand -hex 32)
   ```

## Service URLs

These are configured automatically for Docker networking but can be overridden:

```bash
BACKEND_API_URL=http://backend-api:8000
AGENT_SERVICE_URL=http://agent-service:8083
DB_MCP_SERVER_URL=http://db-mcp-server:8080
TOOLS_MCP_SERVER_URL=http://tools-mcp-server:8080
```

## All Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `ANTHROPIC_API_KEY` | (required) | Anthropic API key |
| `OPENAI_API_KEY` | - | OpenAI API key (optional) |
| `MONGO_USER` | `admin` | MongoDB username |
| `MONGO_PASSWORD` | `chicory` | MongoDB password |
| `MONGO_HOST` | `mongodb` | MongoDB host |
| `MONGO_PORT` | `27017` | MongoDB port |
| `MONGO_DATABASE` | `chicory` | MongoDB database name |
| `REDIS_PASSWORD` | `chicory` | Redis password |
| `REDIS_HOST` | `redis` | Redis host |
| `REDIS_PORT` | `6379` | Redis port |
| `RABBITMQ_USER` | `admin` | RabbitMQ username |
| `RABBITMQ_PASSWORD` | `chicory` | RabbitMQ password |
| `RABBITMQ_HOST` | `rabbitmq` | RabbitMQ host |
| `RABBITMQ_PORT` | `5672` | RabbitMQ port |
| `AWS_ACCESS_KEY_ID` | - | AWS access key |
| `AWS_SECRET_ACCESS_KEY` | - | AWS secret key |
| `AWS_DEFAULT_REGION` | `us-west-2` | AWS region |
| `S3_BUCKET` | - | S3 bucket for file storage |
| `DEBUG` | `false` | Enable debug mode |
| `LOG_LEVEL` | `INFO` | Logging level |
| `JWT_SECRET` | (generated) | JWT signing secret |
| `JWT_ALGORITHM` | `HS256` | JWT algorithm |
| `JWT_EXPIRY_HOURS` | `24` | JWT token expiry |

## Secure Credential Generation

The `generate-secrets.sh` script creates cryptographically secure random passwords:

```bash
./scripts/generate-secrets.sh
```

This updates your `.env` file with secure values for:
- `MONGO_PASSWORD`
- `REDIS_PASSWORD`
- `RABBITMQ_PASSWORD`
- `JWT_SECRET`

## Next Steps

- [Architecture Overview](architecture.md) - Understand how services connect
- [Installation Guide](installation.md) - Get started with Chicory

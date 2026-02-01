# chicory-common

Shared Python utilities for Chicory platform services.

## Installation

```bash
# Install base package
pip install -e packages/python-common

# Install with database support
pip install -e "packages/python-common[database]"

# Install with all extras
pip install -e "packages/python-common[all]"
```

## Usage

```python
from chicory_common import get_settings

settings = get_settings()

# Access configuration
print(settings.mongodb_uri)
print(settings.redis_url)
print(settings.anthropic_api_key)

# Check environment
if settings.is_production:
    print("Running in production mode")

if settings.has_s3_storage:
    print(f"Using S3 bucket: {settings.s3_bucket}")
```

## Configuration

All settings are loaded from environment variables. See `.env.example` in the repository root for all available options.

### Required

- `ANTHROPIC_API_KEY`: Your Anthropic API key for Claude

### Optional

Database, Redis, and RabbitMQ settings have sensible defaults for local development with Docker Compose.

## Development

```bash
# Install dev dependencies
pip install -e "packages/python-common[dev]"

# Run tests
pytest

# Format code
black chicory_common
ruff check chicory_common

# Type check
mypy chicory_common
```

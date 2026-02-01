"""Unified configuration for Chicory services.

All services use these settings for consistent configuration management.
Settings are loaded from environment variables with sensible defaults for local development.
"""

from functools import lru_cache
from typing import Optional

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class ChicorySettings(BaseSettings):
    """Base settings for all Chicory services.

    Environment variables take precedence over defaults.
    For local development, defaults work out of the box with docker-compose.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ==========================================================================
    # API Keys
    # ==========================================================================

    anthropic_api_key: str = Field(
        default="",
        description="Anthropic API key for Claude (required)",
    )

    openai_api_key: Optional[str] = Field(
        default=None,
        description="OpenAI API key (optional, for inference)",
    )

    # ==========================================================================
    # MongoDB Configuration
    # ==========================================================================

    mongodb_uri: str = Field(
        default="mongodb://admin:chicory@mongodb:27017/chicory?authSource=admin",
        description="MongoDB connection URI",
    )

    mongo_user: str = Field(default="admin")
    mongo_password: str = Field(default="chicory")
    mongo_host: str = Field(default="mongodb")
    mongo_port: int = Field(default=27017)
    mongo_database: str = Field(default="chicory")

    # ==========================================================================
    # Redis Configuration
    # ==========================================================================

    redis_url: str = Field(
        default="redis://:chicory@redis:6379",
        description="Redis connection URL",
    )

    redis_password: str = Field(default="chicory")
    redis_host: str = Field(default="redis")
    redis_port: int = Field(default=6379)

    # ==========================================================================
    # RabbitMQ Configuration
    # ==========================================================================

    rabbitmq_url: str = Field(
        default="amqp://admin:chicory@rabbitmq:5672/",
        description="RabbitMQ connection URL",
    )

    rabbitmq_host: str = Field(default="rabbitmq")
    rabbitmq_port: int = Field(default=5672)
    rabbitmq_vhost: str = Field(default="/")
    rabbitmq_user: str = Field(default="admin", alias="rabbitmq_username")
    rabbitmq_password: str = Field(default="chicory")

    # Exchange and queue names
    agent_exchange_name: str = Field(default="task_exchange")
    agent_queue_name: str = Field(default="agent_tasks_queue")
    agent_routing_key: str = Field(default="agent.task")
    training_exchange_name: str = Field(default="training_exchange")
    training_queue_name: str = Field(default="training_queue")
    training_routing_key: str = Field(default="training.job")

    # ==========================================================================
    # AWS Configuration (optional)
    # ==========================================================================

    aws_access_key_id: Optional[str] = Field(default=None)
    aws_secret_access_key: Optional[str] = Field(default=None)
    aws_default_region: str = Field(default="us-west-2")
    s3_bucket: Optional[str] = Field(default=None)

    # ==========================================================================
    # Service URLs (for inter-service communication)
    # ==========================================================================

    backend_api_url: str = Field(
        default="http://backend-api:8000",
        description="URL of the backend API service",
    )

    agent_service_url: str = Field(
        default="http://agent-service:8083",
        description="URL of the agent service",
    )

    db_mcp_server_url: str = Field(
        default="http://db-mcp-server:8080",
        description="URL of the DB MCP server",
    )

    tools_mcp_server_url: str = Field(
        default="http://tools-mcp-server:8080",
        description="URL of the Tools MCP server",
    )

    # ==========================================================================
    # Application Settings
    # ==========================================================================

    debug: bool = Field(default=False)
    log_level: str = Field(default="INFO")

    # JWT for local auth
    jwt_secret: str = Field(
        default="chicory-dev-secret-change-in-production",
        description="Secret key for JWT tokens",
    )
    jwt_algorithm: str = Field(default="HS256")
    jwt_expiry_hours: int = Field(default=24)

    # ==========================================================================
    # Validators
    # ==========================================================================

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        valid_levels = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        upper = v.upper()
        if upper not in valid_levels:
            raise ValueError(f"Invalid log level: {v}. Must be one of {valid_levels}")
        return upper

    # ==========================================================================
    # Computed Properties
    # ==========================================================================

    @property
    def is_production(self) -> bool:
        """Check if running in production mode."""
        return not self.debug

    @property
    def has_aws_credentials(self) -> bool:
        """Check if AWS credentials are configured."""
        return bool(self.aws_access_key_id and self.aws_secret_access_key)

    @property
    def has_s3_storage(self) -> bool:
        """Check if S3 storage is configured."""
        return self.has_aws_credentials and bool(self.s3_bucket)


@lru_cache
def get_settings() -> ChicorySettings:
    """Get cached settings instance.

    Uses lru_cache to ensure settings are only loaded once per process.
    Call get_settings.cache_clear() if you need to reload settings.
    """
    return ChicorySettings()

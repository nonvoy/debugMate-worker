from functools import lru_cache

from pydantic import BaseModel, Field, NonNegativeInt, PositiveInt
from pydantic_settings import BaseSettings, SettingsConfigDict


class OpenSearchIndexConfig(BaseModel):
    """Configuration for OpenSearch index settings."""

    number_of_shards: PositiveInt = Field(default=1, description="Number of shards for the OpenSearch index")
    number_of_replicas: NonNegativeInt = Field(default=0, description="Number of replicas for the OpenSearch index")


class OpenSearchConfig(BaseModel):
    """Configuration for OpenSearch."""

    url: str = Field(..., description="URL of the OpenSearch cluster")
    username: str | None = Field(default=None, description="Username for OpenSearch authentication")
    password: str | None = Field(default=None, description="Password for OpenSearch authentication")
    use_ssl: bool = Field(default=True, description="Use SSL for OpenSearch connection")
    verify_certs: bool = Field(default=True, description="Verify SSL certificates for OpenSearch connection")
    ssl_assert_hostname: bool = Field(default=True, description="Assert hostname for SSL connection")
    ssl_show_warn: bool = Field(default=True, description="Show SSL warnings")
    http_compress: bool = Field(default=True, description="Enable HTTP compression for OpenSearch connection")
    timeout: PositiveInt = Field(default=30, description="Timeout for OpenSearch connection in seconds")
    max_retries: NonNegativeInt = Field(default=3, description="Maximum number of retries for OpenSearch connection")
    retry_on_timeout: bool = Field(default=True, description="Retry on timeout for OpenSearch connection")
    index_config: OpenSearchIndexConfig = Field(default_factory=OpenSearchIndexConfig, description="Configuration for OpenSearch index settings")


class AWSConfig(BaseModel):
    """Configuration for AWS."""

    access_key_id: str | None = Field(default=None, description="AWS access key ID")
    secret_access_key: str | None = Field(default=None, description="AWS secret access key")
    region: str | None = Field(default=None, description="AWS region")


class CeleryConfig(BaseModel):
    """Configuration for Celery."""

    app_name: str = Field(default="debugmate-worker", description="Name of the Celery application")
    task_name: str = Field(default="process_events", description="Name of the Celery task to process events")
    broker_url: str | None = Field(default=None, description="URL of the Celery broker (used only for local environment)")
    endpoint_url: str | None = Field(default=None, description="Custom endpoint URL for the broker")
    is_secure: bool | None = Field(default=None, description="Use SSL when connecting to the broker")
    visibility_timeout: PositiveInt = Field(default=3600, description="Visibility timeout for tasks in seconds")
    polling_interval: PositiveInt = Field(default=5, description="Polling interval for the broker in seconds")
    queue_name: str = Field(default="debugmate-queue", description="Name of the Celery task queue")
    queue_url: str | None = Field(default=None, description="URL of the Celery task queue")


class BasicConfig(BaseSettings):
    """Basic configuration for the application."""

    debug: bool = Field(default=False, description="Enable debug mode")
    log_level: str = Field(default="INFO", description="Logging level for the application")
    environment: str = Field(default="production", description="Environment in which the application is running")
    celery: CeleryConfig = Field(default_factory=CeleryConfig, description="Celery configuration")
    opensearch: OpenSearchConfig = Field(default_factory=OpenSearchConfig, description="OpenSearch configuration")  # type: ignore[arg-type]
    aws: AWSConfig = Field(default_factory=AWSConfig, description="AWS configuration")
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_nested_delimiter="__",
    )


@lru_cache()
def get_config() -> BasicConfig:
    """Returns the basic configuration for the application."""
    return BasicConfig()

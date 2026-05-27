from functools import lru_cache

from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class CeleryConfig(BaseModel):
    """Configuration for Celery."""

    app_name: str = Field(default="debugmate-worker", description="Name of the Celery application")
    task_name: str = Field(default="analyze_events", description="Name of the Celery task to process events")
    broker_url: str = Field(..., description="URL of the message broker")
    endpoint_url: str | None = Field(default=None, description="Custom endpoint URL for the broker")
    is_secure: bool | None = Field(default=None, description="Use SSL when connecting to the broker")
    region: str = Field(default="eu-central-1", description="AWS region for the broker")
    visibility_timeout: int = Field(default=3600, description="Visibility timeout for tasks in seconds")
    polling_interval: int = Field(default=5, description="Polling interval for the broker in seconds")
    queue_name: str = Field(default="debugmate-queue", description="Name of the Celery task queue")


class BasicConfig(BaseSettings):
    """Basic configuration for the application."""

    debug: bool = Field(default=False, description="Enable debug mode")
    log_level: str = Field(default="INFO", description="Logging level for the application")
    celery: CeleryConfig = Field(default_factory=CeleryConfig, description="Celery configuration")  # type: ignore[arg-type]

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_nested_delimiter="__",
    )


@lru_cache()
def get_config() -> BasicConfig:
    """Returns the basic configuration for the application."""
    return BasicConfig()

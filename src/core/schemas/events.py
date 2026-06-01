import datetime as dt
from enum import StrEnum, auto
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class Severity(StrEnum):
    """Enumeration for severity levels of events."""

    debug = auto()
    info = auto()
    warning = auto()
    error = auto()
    critical = auto()


class _BaseEvent(BaseModel):
    service: str = Field(..., description="The name of the service that generated the event", examples=["auth-service", "payment-service"])
    severity: Severity = Field(
        ..., description="The severity level of the event (e.g., 'info', 'warning', 'error')", examples=["info", "warning", "error"]
    )
    environment: str = Field(
        "unknown",
        description="The environment where the event occurred (e.g., 'production', 'staging')",
        examples=["production", "staging"],
    )
    event_type: str = Field("unknown", description="The type of event", examples=["application_log", "security_event"])

    @field_validator("service", "severity", "environment", "event_type", mode="before")
    @classmethod
    def normalize_string_fields(cls, value: object) -> object:
        if isinstance(value, str):
            return value.strip().lower()
        return value


class Event(_BaseEvent):
    """Model representing an event in the system."""

    id: UUID = Field(..., description="The unique identifier of the event", examples=["123e4567-e89b-12d3-a456-426614174000"])
    batch_id: UUID | None = Field(
        None, description="The unique identifier of the batch this event belongs to", examples=["123e4567-e89b-12d3-a456-426614174001"]
    )
    message: str = Field(
        ...,
        min_length=1,
        description="A descriptive message about the event",
        examples=["User login successful", "Payment failed due to insufficient funds"],
    )
    metadata: dict = Field(
        default_factory=dict, description="Additional metadata related to the event", examples=[{"user_id": "12345", "transaction_id": "abcde"}]
    )
    timestamp: dt.datetime = Field(..., description="The timestamp when the event occurred", examples=["2024-06-01T12:00:00Z"])
    published_at: dt.datetime = Field(..., description="The timestamp when the event was published to the system", examples=["2024-06-01T12:05:00Z"])


class NormalizedEvent(Event):
    """Model representing a normalized event, extending the base Event model."""

    normalized_message: str = Field(
        ...,
        min_length=1,
        description="The normalized message of the event",
        examples=["user <email> login successful", "payment <ID> failed due to insufficient funds"],
    )
    fingerprint: str = Field(
        ...,
        description="The fingerprint of the event used for grouping similar events",
        examples=["031edd7d41651593c5fe5c006fa5752b37fddff7bc4e843aa6af0c950f4b9406"],
    )
    incident_id: UUID | None = Field(
        None,
        description="The unique identifier of the incident this event is associated with (if any)",
        examples=["123e4567-e89b-12d3-a456-426614174002"],
    )
    received_at: dt.datetime = Field(..., description="The timestamp when the event was received for processing", examples=["2024-06-01T12:10:00Z"])

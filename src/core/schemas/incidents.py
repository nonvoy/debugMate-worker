import datetime as dt
from enum import StrEnum, auto
from uuid import UUID

from pydantic import BaseModel, Field


class IncidentType(StrEnum):
    """Enumeration for types of incidents."""

    fingerprint = auto()
    environment_service = auto()


class Incident(BaseModel):
    """Model representing an incident in the system."""

    id: UUID = Field(..., description="The unique identifier of the incident", examples=["123e4567-e89b-12d3-a456-426614174000"])
    type: IncidentType = Field(
        ..., description="The type of incident (e.g., 'fingerprint', 'environment_service')", examples=["fingerprint", "environment_service"]
    )
    fingerprint: str | None = Field(None, description="The fingerprint associated with the incident (if applicable)", examples=["abc123def456"])
    environment: str | None = Field(
        None, description="The environment associated with the incident (if applicable)", examples=["production", "staging"]
    )
    service: str | None = Field(
        None, description="The service associated with the incident (if applicable)", examples=["auth-service", "payment-service"]
    )
    events: list[UUID] = Field(..., description="A list of event IDs that are part of this incident")
    start_time: dt.datetime = Field(..., description="The start of the incident time frame", examples=["2024-06-01T12:00:00Z"])
    end_time: dt.datetime | None = Field(None, description="The end of the incident time frame", examples=["2024-06-01T12:10:00Z"])
    created_at: dt.datetime = Field(..., description="The timestamp when the incident was created", examples=["2024-06-01T12:05:00Z"])
    updated_at: dt.datetime = Field(..., description="The timestamp when the incident was last updated", examples=["2024-06-01T12:10:00Z"])

import datetime as dt
from enum import StrEnum, auto
from uuid import UUID

from pydantic import BaseModel, Field


class IncidentType(StrEnum):
    """Enumeration for types of incidents."""

    fingerprint = auto()
    environment_service = auto()


class IncidentStatus(StrEnum):
    """Enumeration representing the status of an incident."""

    OPEN = auto()
    ASSIGNED = auto()
    RESOLVED = auto()


class Incident(BaseModel):
    """Model representing an incident in the system."""

    type: IncidentType = Field(
        ..., description="The type of incident (e.g., 'fingerprint', 'environment_service')", examples=["fingerprint", "environment_service"]
    )
    fingerprint: str | None = Field(None, description="The fingerprint associated with the incident (if applicable)", examples=["abc123def456"])
    environment: str = Field(..., description="The environment associated with the incident (if applicable)", examples=["production", "staging"])
    service: str = Field(..., description="The service associated with the incident (if applicable)", examples=["auth-service", "payment-service"])
    events: set[UUID] = Field(..., description="A list of event IDs that are part of this incident")
    start_time: dt.datetime = Field(..., description="The start of the incident time frame", examples=["2024-06-01T12:00:00Z"])
    end_time: dt.datetime = Field(..., description="The end of the incident time frame", examples=["2024-06-01T12:10:00Z"])
    status: IncidentStatus = Field(
        default=IncidentStatus.OPEN, description="The current status of the incident", examples=["open", "assigned", "resolved"]
    )
    comment: str | None = Field(
        default=None,
        description="An optional comment providing additional information about the incident",
        examples=["This incident is being investigated."],
    )
    assigned_to: str | None = Field(
        default=None,
        description="The name of the person or team assigned to handle the incident",
        examples=["John Doe", "Team Alpha"],
    )
    created_at: dt.datetime = Field(..., description="The timestamp when the incident was created", examples=["2024-06-01T12:05:00Z"])
    updated_at: dt.datetime = Field(..., description="The timestamp when the incident was last updated", examples=["2024-06-01T12:10:00Z"])

import datetime as dt
from enum import StrEnum, auto
from uuid import UUID

from pydantic import BaseModel, Field, PositiveInt


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
    """Schema representing an incident in the system."""

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


class IncidentGet(Incident):
    """Schema for retrieving an incident, including its unique ID."""

    id: PositiveInt = Field(..., description="The unique identifier of the incident", examples=[1])


class LLMResponseConfidence(StrEnum):
    """Enumeration representing the confidence level of the analysis provided by the language model."""

    LOW = auto()
    MEDIUM = auto()
    HIGH = auto()


class IncidentAnalysis(BaseModel):
    """Schema representing the analysis results of an incident."""

    summary: str = Field(
        ..., description="A concise summary of the incident analysis", examples=["The incident was caused by a database connection failure."]
    )
    root_cause: str = Field(
        ..., description="The most likely root cause of the incident", examples=["Database connection failure due to network issues."]
    )
    confidence: LLMResponseConfidence = Field(..., description="The confidence level of the analysis", examples=["low", "medium", "high"])
    recommendations: list[str] = Field(
        ...,
        description="A list of recommended actions to address the incident",
        examples=[["Restart the database server", "Check network connectivity"]],
    )

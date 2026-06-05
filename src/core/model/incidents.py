import datetime as dt
from uuid import UUID

from pydantic import PositiveInt
from sqlalchemy import Column, DateTime
from sqlmodel import Field, SQLModel

from src.config.basic_config import get_config
from src.core.schemas.incidents import IncidentStatus, IncidentType

config = get_config()


class Incident(SQLModel, table=True):
    """Model representing an incident."""

    __tablename__ = "incidents"

    id: PositiveInt | None = Field(default=None, primary_key=True)
    type: IncidentType = Field(..., description="The type of the incident (e.g., 'fingerprint', 'environment_service').", nullable=False)
    fingerprint: str | None = Field(None, description="The fingerprint of the incident used for grouping similar events.", nullable=True)
    environment: str = Field(..., description="The environment in which the incident occurred (e.g., 'production', 'staging').", nullable=False)
    service: str = Field(..., description="The service in which the incident occurred (e.g., 'auth-service', 'payment-service').", nullable=False)
    start_time: dt.datetime = Field(
        ...,
        sa_column=Column(DateTime(timezone=True), nullable=False),
        description="The date and time when the incident started.",
    )
    end_time: dt.datetime = Field(
        ...,
        sa_column=Column(DateTime(timezone=True), nullable=False),
        description="The date and time when the incident ended.",
    )
    status: IncidentStatus = Field(default=IncidentStatus.OPEN, description="The current status of the incident.", nullable=False)
    comment: str | None = Field(None, description="An optional comment providing additional information about the incident.", nullable=True)
    assigned_to: str | None = Field(None, description="The name of the person or team assigned to handle the incident.", nullable=True)
    created_at: dt.datetime = Field(
        ...,
        sa_column=Column(DateTime(timezone=True), nullable=False),
        description="The date and time when the incident was created.",
    )
    updated_at: dt.datetime = Field(
        ...,
        sa_column=Column(DateTime(timezone=True), nullable=False),
        description="The date and time when the incident was last updated.",
    )


class EventsInIncident(SQLModel, table=True):
    """Model representing the relationship between events and incidents."""

    __tablename__ = "events_in_incidents"

    event_id: UUID = Field(..., primary_key=True, nullable=False, description="The unique identifier of the event.")
    incident_id: PositiveInt = Field(
        ..., foreign_key="incidents.id", nullable=False, description="The unique identifier of the incident to which the event belongs."
    )
    associated_at: dt.datetime = Field(
        ...,
        sa_column=Column(DateTime(timezone=True), nullable=False),
        description="The date and time when the event was associated with the incident.",
    )

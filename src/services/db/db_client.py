import datetime as dt
from functools import lru_cache
from uuid import UUID

from pydantic import PositiveInt
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, SQLModel, col, create_engine, select

from src.config.basic_config import get_config
from src.config.logger import get_logger
from src.core.model.incidents import EventsInIncident, Incident, IncidentAnalysis
from src.core.schemas.events import NormalizedEvent
from src.core.schemas.incidents import Incident as IncidentSchema
from src.core.schemas.incidents import IncidentAnalysisSchema, IncidentGet

config = get_config()
logger = get_logger(__name__)


class DBClient:
    """Singleton class to manage database operations."""

    def __init__(self):
        self.engine = create_engine(config.db_url)
        SQLModel.metadata.create_all(self.engine)

    def return_uuids_of_events_with_incidents(self, events: list[NormalizedEvent]) -> set[UUID]:
        """Returns a set of UUIDs of events that are already associated with an incident."""
        with Session(self.engine) as session:
            event_ids = [event.id for event in events]
            statement = select(EventsInIncident.event_id).where(col(EventsInIncident.event_id).in_(event_ids))
            result = session.exec(statement).all()
            return set(result)

    def save_incident(self, incident: IncidentSchema) -> int | None:
        """Saves a single incident and its associated events to the database.
        Returns the ID of the saved incident or None if saving failed.
        """
        with Session(self.engine) as session:
            try:
                db_incident = Incident(**incident.model_dump(exclude={"events"}))
                session.add(db_incident)
                session.flush()  # Flush to get the generated ID for the incident
                incident_id = db_incident.id
                events_in_incident = [
                    EventsInIncident(
                        incident_id=incident_id,
                        event_id=event_id,
                        associated_at=db_incident.created_at,
                    )
                    for event_id in incident.events
                ]
                session.add_all(events_in_incident)
                session.commit()
            except IntegrityError as e:
                logger.error(f"Failed to save incident due to integrity error: {e}")
                session.rollback()
                return None

        logger.info(f"Saved incident {incident_id} with {len(events_in_incident)} associated events to the database")
        return incident_id

    def save_incidents(self, incidents: list[IncidentSchema]) -> list[int]:
        """Saves multiple incidents and their associated events to the database.
        Returns a list of IDs of the saved incidents.
        """
        saved_incident_ids = []
        for incident in incidents:
            incident_id = self.save_incident(incident)
            if incident_id is not None:
                saved_incident_ids.append(incident_id)
        return saved_incident_ids

    def _get_events_of_incident(self, incident_id: PositiveInt) -> list[UUID]:
        """Returns a list of event IDs associated with a given incident ID."""
        with Session(self.engine) as session:
            statement = select(EventsInIncident.incident_id, EventsInIncident.event_id).where(EventsInIncident.incident_id == incident_id)
            result = session.exec(statement).all()
            return [row[1] for row in result]

    def get_incident_by_id(self, incident_id: PositiveInt) -> IncidentGet | None:
        """Returns the incident with the given ID, or None if not found."""
        with Session(self.engine) as session:
            incident = session.get(Incident, incident_id)
            if incident:
                incident_dict = incident.model_dump()
                incident_id = incident_dict["id"]
                incident_dict["events"] = self._get_events_of_incident(incident_id)
                return IncidentGet.model_validate(incident_dict)

        return None

    def save_incident_analysis(
        self, analysis_result: IncidentAnalysisSchema, incident_id: PositiveInt, task_id: UUID
    ) -> tuple[PositiveInt, UUID] | None:
        """Saves the analysis result of an incident to the database."""
        with Session(self.engine) as session:
            try:
                db_analysis = IncidentAnalysis(
                    **analysis_result.model_dump(), incident_id=incident_id, task_id=task_id, created_at=dt.datetime.now(dt.timezone.utc)
                )
                session.add(db_analysis)
                session.commit()
            except IntegrityError as e:
                logger.error(f"Failed to save incident analysis due to integrity error: {e}")
                session.rollback()
                return None

        return (incident_id, task_id)


@lru_cache()
def get_db_client() -> DBClient:
    """Returns a singleton instance of the DBClient."""
    return DBClient()

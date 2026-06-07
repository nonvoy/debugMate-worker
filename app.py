import datetime as dt

from src.config.basic_config import get_config
from src.config.logger import get_logger
from src.core.events import normalize_event
from src.core.incidents import check_for_incidents
from src.services.celery.worker import create_celery_app
from src.services.db.db_client import get_db_client
from src.services.openai.openai_client import get_openai_client
from src.services.search.open_search_client import get_opensearch_client

config = get_config()
logger = get_logger(__name__)

celery_app = create_celery_app()


@celery_app.task(name="process_events", bind=True)
def process_events(self, event_payload: list[dict]) -> None:
    """Celery task to process events."""
    received_at = dt.datetime.now(dt.timezone.utc)
    opensearch_client = get_opensearch_client()
    db_client = get_db_client()
    normalized_events = [normalize_event(event, received_at) for event in event_payload]
    incidents = check_for_incidents(opensearch_client, db_client, normalized_events)
    indexed_event_count = opensearch_client.index_events(normalized_events)
    logger.info(f"Indexed {indexed_event_count} out of {len(normalized_events)} events into OpenSearch")
    saved_incidents = db_client.save_incidents(incidents)
    logger.info(f"Saved {len(saved_incidents)} out of {len(incidents)} incidents into the database")


@celery_app.task(name="send_incident_for_analysis", bind=True)
def send_incident_for_analysis(self, incident_id: str) -> None:
    """Celery task to send an incident for analysis."""
    received_at = dt.datetime.now(dt.timezone.utc)
    task_id = self.request.id
    logger.info(f"Received task {task_id} to analyze incident with ID: {incident_id} at {received_at}")

    db_client = get_db_client()
    opensearch_client = get_opensearch_client()
    openai_client = get_openai_client()

    incident = db_client.get_incident_by_id(incident_id)
    if not incident:
        logger.error(f"Incident with ID {incident_id} not found in the database. Terminating analysis for task {task_id}.")
        return

    events = opensearch_client.get_events(incident.events)
    if not events:
        logger.warning(f"No events found for incident with ID {incident_id}. Proceeding with analysis using only incident data for task {task_id}.")
        return

    analysis_result = openai_client.analyze_incident(incident, events)
    save_result = db_client.save_incident_analysis(analysis_result, incident.id, task_id)
    if save_result is None:
        logger.error(f"Failed to save analysis results for incident with ID: {incident_id} and task {task_id}.")
    else:
        logger.info(f"Completed analysis for incident with ID: {incident_id} and saved results to the database for task {task_id}.")

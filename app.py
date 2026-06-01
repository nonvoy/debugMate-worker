import datetime as dt

from src.config.basic_config import get_config
from src.config.logger import get_logger
from src.core.events import normalize_event
from src.core.incidents import check_for_incidents
from src.services.celery.worker import create_celery_app
from src.services.search.open_search_client import get_opensearch_client

config = get_config()
logger = get_logger(__name__)

celery_app = create_celery_app()


@celery_app.task(name=config.celery.task_name, bind=True)
def process_events(self, event_payload: list[dict]) -> None:
    """Celery task to process events."""
    opensearch_client = get_opensearch_client()
    received_at = dt.datetime.now(dt.timezone.utc)
    normalized_events = [normalize_event(event, received_at) for event in event_payload]
    incidents = check_for_incidents(opensearch_client, normalized_events)
    indexed_event_count = opensearch_client.index_events(normalized_events)
    logger.info(f"Indexed {indexed_event_count} events into OpenSearch")
    indexed_incident_count = opensearch_client.index_incidents(incidents)
    logger.info(f"Indexed {indexed_incident_count} incidents into OpenSearch")

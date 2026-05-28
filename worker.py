import datetime as dt

from celery import Celery

from src.config.basic_config import get_config
from src.config.logger import get_logger
from src.core.events import normalize_event
from src.services.search.indexes.events import index_events
from src.services.search.open_search_client import get_opensearch_client

config = get_config()
logger = get_logger(__name__)

broker_transport_options = {
    "region": config.celery.region,
    "visibility_timeout": config.celery.visibility_timeout,
    "polling_interval": config.celery.polling_interval,
}

if config.environment != "local":
    broker_transport_options["predefined_queues"] = {
        config.celery.queue_name: {
            "url": config.celery.queue_url,
        },
    }

if config.celery.endpoint_url:
    broker_transport_options["endpoint_url"] = config.celery.endpoint_url

if config.celery.is_secure is not None:
    broker_transport_options["is_secure"] = config.celery.is_secure

celery_app = Celery(
    config.celery.app_name,
    broker=config.celery.broker_url,
)

celery_app.conf.update(
    broker_transport_options=broker_transport_options,
    task_default_queue=config.celery.queue_name,
)


@celery_app.task(name=config.celery.task_name, bind=True)
def analyze_events(self, event_payload: list[dict]):
    """Celery task to analyze events."""
    opensearch_client = get_opensearch_client()
    received_at = dt.datetime.now(dt.timezone.utc)
    normalized_events = [normalize_event(event, received_at) for event in event_payload]
    indexed_count = index_events(opensearch_client, normalized_events)
    logger.info(f"Indexed {indexed_count} events into OpenSearch")

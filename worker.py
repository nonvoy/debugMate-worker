import datetime as dt

from celery import Celery
from kombu.utils.url import safequote

from src.config.basic_config import get_config
from src.config.logger import get_logger
from src.core.events import normalize_event
from src.services.search.indexes.events import index_events
from src.services.search.open_search_client import get_opensearch_client

config = get_config()
logger = get_logger(__name__)

broker_transport_options = {
    "region": config.aws.region,
    "visibility_timeout": config.celery.visibility_timeout,
    "polling_interval": config.celery.polling_interval,
}

# URL-encode ONLY for broker URL
aws_access_key_encoded = safequote(config.aws.access_key_id)
aws_secret_key_encoded = safequote(config.aws.secret_access_key)

if config.environment != "local":
    broker_transport_options["predefined_queues"] = {
        config.celery.queue_name: {
            "url": config.celery.queue_url,
            "access_key_id": config.aws.access_key_id,
            "secret_access_key": config.aws.secret_access_key,
        },
    }

if config.celery.endpoint_url:
    broker_transport_options["endpoint_url"] = config.celery.endpoint_url

if config.celery.is_secure is not None:
    broker_transport_options["is_secure"] = config.celery.is_secure

celery_app = Celery(
    config.celery.app_name,
    broker=f"sqs://{aws_access_key_encoded}:{aws_secret_key_encoded}@",
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

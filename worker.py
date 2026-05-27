import datetime as dt

from celery import Celery

from src.config.basic_config import get_config
from src.core.events import normalize_event

config = get_config()

broker_transport_options = {
    "region": config.celery.region,
    "visibility_timeout": config.celery.visibility_timeout,
    "polling_interval": config.celery.polling_interval,
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
    received_at = dt.datetime.now(dt.timezone.utc)
    normalized_events = [normalize_event(event, received_at) for event in event_payload]  # noqa: F841 - temporary workaround to avoid unused variable warning

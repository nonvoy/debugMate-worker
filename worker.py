from celery import Celery

from src.config.basic_config import get_config

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

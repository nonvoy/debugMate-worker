from functools import lru_cache

from celery import Celery
from kombu.utils.url import safequote

from src.config.basic_config import get_config
from src.config.logger import get_logger

config = get_config()
logger = get_logger(__name__)


def _create_celery_instance_with_sqs():
    """Factory function to create a Celery instance with SQS broker."""
    aws_access_key_encoded = safequote(config.aws.access_key_id)
    aws_secret_key_encoded = safequote(config.aws.secret_access_key)

    celery_app = Celery(
        config.celery.app_name,
        broker=f"sqs://{aws_access_key_encoded}:{aws_secret_key_encoded}@",
    )

    broker_transport_options = {
        "region": config.aws.region,
        "visibility_timeout": config.celery.visibility_timeout,
        "polling_interval": config.celery.polling_interval,
        "endpoint_url": config.celery.endpoint_url,
        "is_secure": config.celery.is_secure,
        "predefined_queues": {
            config.celery.queue_name: {
                "url": config.celery.queue_url,
                "access_key_id": config.aws.access_key_id,
                "secret_access_key": config.aws.secret_access_key,
            },
        },
    }

    celery_app.conf.update(
        broker_transport_options=broker_transport_options,
        task_default_queue=config.celery.queue_name,
    )

    return celery_app


def _create_celery_instance_with_redis():
    """Factory function to create a Celery instance with Redis broker."""
    celery_app = Celery(config.celery.app_name, broker=config.celery.broker_url)
    return celery_app


@lru_cache()
def create_celery_app():
    """Factory function to create a Celery app instance based on the environment."""
    if config.environment == "local":
        logger.info("Creating Celery app with Redis broker for local environment")
        return _create_celery_instance_with_redis()
    else:
        logger.info("Creating Celery app with SQS broker for non-local environment")
        return _create_celery_instance_with_sqs()

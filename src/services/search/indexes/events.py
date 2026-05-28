from opensearchpy import OpenSearch
from opensearchpy.helpers import bulk

from src.config.basic_config import get_config
from src.core.schemas.events import NormalizedEvent

config = get_config()

EVENTS_INDEX = "debugmate-events"

EVENTS_INDEX_BODY = {
    "settings": {
        "index": {
            "number_of_shards": config.opensearch.index_config.number_of_shards,
            "number_of_replicas": config.opensearch.index_config.number_of_replicas,
        }
    },
    "mappings": {
        "properties": {
            "id": {"type": "keyword"},
            "batch_id": {"type": "keyword"},
            "service": {"type": "keyword"},
            "severity": {"type": "keyword"},
            "environment": {"type": "keyword"},
            "event_type": {"type": "keyword"},
            "message": {"type": "text"},
            "normalized_message": {"type": "text"},
            "metadata": {"type": "object", "enabled": True},
            "fingerprint": {"type": "keyword"},
            "timestamp": {"type": "date"},
            "published_at": {"type": "date"},
            "received_at": {"type": "date"},
        }
    },
}


def create_events_index_if_not_exists(opensearch_client: OpenSearch) -> None:
    """Checks if the events index exists in OpenSearch, and creates it if it doesn't."""
    exists = opensearch_client.indices.exists(index=EVENTS_INDEX)

    if not exists:
        opensearch_client.indices.create(
            index=EVENTS_INDEX,
            body=EVENTS_INDEX_BODY,
        )


def index_events(opensearch_client: OpenSearch, events: list[NormalizedEvent]) -> int:
    """Indexes a list of normalized events into OpenSearch. Returns the number of successfully indexed events."""
    actions = [
        {
            "_op_type": "index",
            "_index": EVENTS_INDEX,
            "_id": str(event.id),
            "_source": event.model_dump(mode="json"),
        }
        for event in events
    ]

    success_count, _ = bulk(
        client=opensearch_client,
        actions=actions,
        raise_on_error=False,
    )

    return success_count

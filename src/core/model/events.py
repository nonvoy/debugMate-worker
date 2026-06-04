from src.config.basic_config import get_config

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
            "incident_id": {"type": "keyword"},
            "timestamp": {"type": "date"},
            "published_at": {"type": "date"},
            "received_at": {"type": "date"},
            "updated_at": {"type": "date"},
        }
    },
}

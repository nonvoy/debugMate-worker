from src.config.basic_config import get_config

config = get_config()

INCIDENTS_INDEX = "debugmate-incidents"

INCIDENTS_INDEX_BODY = {
    "settings": {
        "index": {
            "number_of_shards": config.opensearch.index_config.number_of_shards,
            "number_of_replicas": config.opensearch.index_config.number_of_replicas,
        }
    },
    "mappings": {
        "properties": {
            "id": {"type": "keyword"},
            "type": {"type": "keyword"},
            "fingerprint": {"type": "keyword"},
            "environment": {"type": "keyword"},
            "service": {"type": "keyword"},
            "events": {"type": "keyword"},
            "start_time": {"type": "date"},
            "end_time": {"type": "date"},
            "created_at": {"type": "date"},
            "updated_at": {"type": "date"},
        }
    },
}

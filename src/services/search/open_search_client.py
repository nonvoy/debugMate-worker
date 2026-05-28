from functools import lru_cache

from opensearchpy import OpenSearch

from src.config.basic_config import get_config
from src.services.search.indexes.events import create_events_index_if_not_exists


@lru_cache()
def get_opensearch_client() -> OpenSearch:
    """Initializes OpenSearch client and creates required indexes. Returns the initialized client."""
    config = get_config()
    http_auth = None
    if config.opensearch.username and config.opensearch.password:
        http_auth = (
            config.opensearch.username,
            config.opensearch.password,
        )

    client = OpenSearch(
        hosts=[config.opensearch.url],
        http_compress=config.opensearch.http_compress,
        verify_certs=config.opensearch.verify_certs,
        timeout=config.opensearch.timeout,
        max_retries=config.opensearch.max_retries,
        retry_on_timeout=config.opensearch.retry_on_timeout,
        http_auth=http_auth,
    )

    # Create the required indexes
    create_events_index_if_not_exists(client)

    return client

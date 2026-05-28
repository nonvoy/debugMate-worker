from functools import lru_cache

from opensearchpy import OpenSearch

from src.config.basic_config import get_config


@lru_cache()
def get_opensearch_client() -> OpenSearch:
    """Returns an OpenSearch client instance."""
    config = get_config()
    params = {
        "hosts": [config.opensearch.url],
        "http_compress": config.opensearch.http_compress,
        "verify_certs": config.opensearch.verify_certs,
        "timeout": config.opensearch.timeout,
        "max_retries": config.opensearch.max_retries,
        "retry_on_timeout": config.opensearch.retry_on_timeout,
    }

    if config.opensearch.username and config.opensearch.password:
        params["http_auth"] = (
            config.opensearch.username,
            config.opensearch.password,
        )

    return OpenSearch(**params)
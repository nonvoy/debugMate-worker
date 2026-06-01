import datetime as dt
from functools import lru_cache

from opensearchpy import OpenSearch, TransportError
from opensearchpy.helpers import bulk

from src.config.basic_config import get_config
from src.config.logger import get_logger
from src.core.schemas.events import NormalizedEvent
from src.services.search.indexes.events import EVENTS_INDEX, EVENTS_INDEX_BODY

config = get_config()
logger = get_logger(__name__)


class OpenSearchClient:
    """Singleton class to manage OpenSearch client instance."""

    def __init__(self):
        http_auth = None
        if config.opensearch.username and config.opensearch.password:
            http_auth = (
                config.opensearch.username,
                config.opensearch.password,
            )
        self.__client = OpenSearch(
            hosts=[config.opensearch.url],
            http_compress=config.opensearch.http_compress,
            verify_certs=config.opensearch.verify_certs,
            timeout=config.opensearch.timeout,
            max_retries=config.opensearch.max_retries,
            retry_on_timeout=config.opensearch.retry_on_timeout,
            http_auth=http_auth,
        )
        self.__create_events_index_if_not_exists()

    def __create_events_index_if_not_exists(self) -> None:
        """Checks if the events index exists in OpenSearch, and creates it if it doesn't."""
        exists = self.__client.indices.exists(index=EVENTS_INDEX)
        if not exists:
            self.__client.indices.create(
                index=EVENTS_INDEX,
                body=EVENTS_INDEX_BODY,
            )

    def index_events(self, events: list[NormalizedEvent]) -> int:
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
        try:
            success_count, _ = bulk(
                client=self.__client,
                actions=actions,
                raise_on_error=True,
            )
        except TransportError as e:
            logger.error(f"Error indexing events: {e.info}")
            success_count = 0
        except Exception as e:
            logger.error(f"Unexpected error indexing events: {str(e)}")
            success_count = 0

        return success_count

    def fetch_events_for_given_timestamp_range(self, start_time: dt.datetime, end_time: dt.datetime) -> list[NormalizedEvent]:
        """Fetches events from OpenSearch that occurred within the given timestamp range."""
        events = []
        query = {
            "query": {
                "range": {
                    "timestamp": {
                        "gte": start_time.isoformat(),
                        "lte": end_time.isoformat(),
                    }
                }
            },
        }
        try:
            response = self.__client.search(index=EVENTS_INDEX, body=query)
            hits = response.get("hits", {}).get("hits", [])
            events = [NormalizedEvent.model_validate(hit["_source"]) for hit in hits]
        except TransportError as e:
            logger.error(f"Error fetching events: {e.info}")
        except Exception as e:
            logger.error(f"Unexpected error fetching events: {str(e)}")

        return events


@lru_cache()
def get_opensearch_client() -> OpenSearchClient:
    """Initializes OpenSearch client and creates required indexes. Returns the initialized client."""
    return OpenSearchClient()

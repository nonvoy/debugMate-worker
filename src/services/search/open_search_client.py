import datetime as dt
from functools import lru_cache

from opensearchpy import OpenSearch, TransportError
from opensearchpy.helpers import bulk

from src.config.basic_config import get_config
from src.config.logger import get_logger
from src.core.model.events import EVENTS_INDEX, EVENTS_INDEX_BODY
from src.core.model.incidents import INCIDENTS_INDEX, INCIDENTS_INDEX_BODY
from src.core.schemas.events import NormalizedEvent
from src.core.schemas.incidents import Incident

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
        self.__create_incidents_index_if_not_exists()

    def __create_events_index_if_not_exists(self) -> None:
        """Checks if the events index exists in OpenSearch, and creates it if it doesn't."""
        exists = self.__client.indices.exists(index=EVENTS_INDEX)
        if not exists:
            self.__client.indices.create(
                index=EVENTS_INDEX,
                body=EVENTS_INDEX_BODY,
            )

    def __create_incidents_index_if_not_exists(self) -> None:
        """Checks if the incidents index exists in OpenSearch, and creates it if it doesn't."""
        exists = self.__client.indices.exists(index=INCIDENTS_INDEX)
        if not exists:
            self.__client.indices.create(
                index=INCIDENTS_INDEX,
                body=INCIDENTS_INDEX_BODY,
            )

    def index_events(self, events: list[NormalizedEvent]) -> int:
        """Indexes a list of normalized events into OpenSearch. Returns the number of successfully indexed events."""
        if len(events) == 0:
            return 0

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

    def index_incidents(self, incidents: list[Incident]) -> int:
        """Indexes a list of incidents into OpenSearch. Returns the number of successfully indexed incidents."""
        if len(incidents) == 0:
            return 0

        actions = [
            {
                "_op_type": "index",
                "_index": INCIDENTS_INDEX,
                "_id": str(incident.id),
                "_source": incident.model_dump(mode="json"),
            }
            for incident in incidents
        ]
        success_count = 0
        try:
            success_count, _ = bulk(
                client=self.__client,
                actions=actions,
                raise_on_error=True,
            )
        except TransportError as e:
            logger.error(f"Error indexing incidents: {e.info}")
        except Exception as e:
            logger.error(f"Unexpected error indexing incidents: {str(e)}")

        return success_count

    def update_events_with_incidents(self, incidents: list[Incident]) -> int:
        """Updates events in OpenSearch to associate them with their corresponding incidents. Returns the number of successfully updated events."""
        if len(incidents) == 0:
            return 0

        now = dt.datetime.now(dt.timezone.utc)
        event_incident_map: dict[str, str] = {}
        for incident in incidents:
            for event_id in incident.events:
                event_incident_map[str(event_id)] = str(incident.id)

        actions = []
        for event_document_id, incident_id in event_incident_map.items():
            action = {
                "_op_type": "update",
                "_index": EVENTS_INDEX,
                "_id": event_document_id,
                "doc": {
                    "incident_id": incident_id,
                    "updated_at": now.isoformat(),
                },
            }
            actions.append(action)

        success_count = 0
        try:
            success_count, _ = bulk(
                client=self.__client,
                actions=actions,
                raise_on_error=True,
            )
        except TransportError as e:
            logger.error(f"Error updating events with incidents: {e.info}")
        except Exception as e:
            logger.error(f"Unexpected error updating events with incidents: {str(e)}")

        return success_count


@lru_cache()
def get_opensearch_client() -> OpenSearchClient:
    """Initializes OpenSearch client and creates required indexes. Returns the initialized client."""
    return OpenSearchClient()

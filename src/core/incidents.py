import datetime as dt
import uuid

from src.config.basic_config import get_config
from src.core.schemas.events import NormalizedEvent
from src.core.schemas.incidents import Incident, IncidentType
from src.services.search.open_search_client import OpenSearchClient

config = get_config()


def _get_time_range(events: list[NormalizedEvent]) -> tuple[dt.datetime, dt.datetime]:
    """Get the minimum and maximum timestamps from the list of normalized events."""
    timestamps = [event.received_at for event in events]
    min_timestamp = min(timestamps)
    max_timestamp = max(timestamps)

    return min_timestamp, max_timestamp


def _group_events_by_fingerprint(events: list[NormalizedEvent]) -> dict[str, list[NormalizedEvent]]:
    """Group events by their fingerprint."""
    grouped: dict[str, list[NormalizedEvent]] = {}
    for event in events:
        if event.fingerprint not in grouped:
            grouped[event.fingerprint] = []
        grouped[event.fingerprint].append(event)

    return grouped


def _identify_incidents_by_fingerprint_by_sliding_window(fingerprint: str, events: list[NormalizedEvent]) -> list[Incident]:
    """Identify potential incidents based on a sliding window approach for events with the same fingerprint."""
    incidents = []

    # Drop events that are already associated with an incident
    events = [event for event in events if event.incident_id is None]

    # Slide window through the events to check for incidents within the time window
    win_start_time = events[0].timestamp
    win_end_time = win_start_time + dt.timedelta(seconds=config.incident.time_interval)
    ix = 0
    while ix < len(events):
        win_events = [event for event in events if win_start_time <= event.timestamp <= win_end_time]
        if len(win_events) < config.incident.fingerprint_threshold:
            # Not enough events in the current window, move the window forward to the next event
            ix += 1
            win_start_time = events[ix].timestamp if ix < len(events) else win_start_time
            win_end_time = win_start_time + dt.timedelta(seconds=config.incident.time_interval)
            continue

        # We found a window with enough events to create an incident
        incident = Incident(
            id=uuid.uuid4(),
            type=IncidentType.fingerprint,
            fingerprint=fingerprint,
            environment=None,
            service=None,
            events=[event.id for event in win_events],
            start_time=win_start_time,
            end_time=win_end_time,
            created_at=dt.datetime.now(dt.timezone.utc),
            updated_at=dt.datetime.now(dt.timezone.utc),
        )
        incidents.append(incident)

        # Move the window forward after the end of the current window
        ix += len(win_events)
        win_start_time = events[ix].timestamp
        win_end_time = win_start_time + dt.timedelta(seconds=config.incident.time_interval)

    return incidents


def _identify_incidents_by_fingerprint(grouped_events: dict[str, list[NormalizedEvent]]) -> list[Incident]:
    """Identify potential incidents based on grouped events by fingerprint."""
    incidents = []
    for fingerprint, events in grouped_events.items():
        # Drop events that are already associated with an incident
        events = [event for event in events if event.incident_id is None]

        if len(events) < config.incident.fingerprint_threshold:
            # Not enough events with the same fingerprint to create an incident
            continue

        start_time, end_time = _get_time_range(events)
        time_diff = end_time - start_time
        if time_diff <= dt.timedelta(seconds=config.incident.time_interval):
            # All events with the same fingerprint occurred within the time interval, create an incident
            incident = Incident(
                id=uuid.uuid4(),
                type=IncidentType.fingerprint,
                fingerprint=fingerprint,
                environment=None,
                service=None,
                events=[event.id for event in events],
                start_time=start_time,
                end_time=end_time,
                created_at=dt.datetime.now(dt.timezone.utc),
                updated_at=dt.datetime.now(dt.timezone.utc),
            )
            incidents.append(incident)
            continue

        incidents.extend(_identify_incidents_by_fingerprint_by_sliding_window(fingerprint, events))

    return incidents


def check_for_incidents(opensearch_client: OpenSearchClient, normalized_events: list[NormalizedEvent]) -> list[Incident]:
    """Checks for potential incidents based on the normalized events and creates incidents if thresholds are met."""
    min_timestamp, max_timestamp = _get_time_range(normalized_events)
    earlier_events = opensearch_client.fetch_events_for_given_timestamp_range(
        min_timestamp - dt.timedelta(seconds=config.incident.time_interval), min_timestamp
    )
    later_events = opensearch_client.fetch_events_for_given_timestamp_range(
        max_timestamp, max_timestamp + dt.timedelta(seconds=config.incident.time_interval)
    )
    all_events = earlier_events + normalized_events + later_events
    group_by_fingerprint = _group_events_by_fingerprint(all_events)
    incidents_by_fingerprint = _identify_incidents_by_fingerprint(group_by_fingerprint)

    return incidents_by_fingerprint

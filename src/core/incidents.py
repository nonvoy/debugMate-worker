import datetime as dt
import uuid

from src.config.basic_config import get_config
from src.core.schemas.events import NormalizedEvent, Severity
from src.core.schemas.incidents import Incident, IncidentType
from src.services.db.db_client import DBClient
from src.services.search.open_search_client import OpenSearchClient

config = get_config()


def _get_time_range(events: list[NormalizedEvent]) -> tuple[dt.datetime, dt.datetime]:
    """Get the minimum and maximum timestamps from the list of normalized events."""
    timestamps = [event.timestamp for event in events]
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


def _group_events_by_environment_and_service(events: list[NormalizedEvent]) -> dict[tuple[str, str], list[NormalizedEvent]]:
    """Group events by their environment and service."""
    grouped: dict[tuple[str, str], list[NormalizedEvent]] = {}
    for event in events:
        _key = (event.environment, event.service)
        if _key not in grouped:
            grouped[_key] = []
        grouped[_key].append(event)

    return grouped


def _identify_incidents_by_sliding_window(incident_type: IncidentType, events: list[NormalizedEvent]) -> list[Incident]:
    """Identify potential incidents based on a sliding window approach for the given events."""
    # Determine the incident threshold and grouping criteria based on the incident type
    if incident_type == IncidentType.fingerprint:
        incident_threshold = config.incident.fingerprint_threshold
        fingerprint = events[0].fingerprint
    else:
        incident_threshold = config.incident.service_env_threshold
        fingerprint = None

    environment = events[0].environment
    service = events[0].service

    # Slide window through the events to check for incidents within the time window
    win_start_time = events[0].timestamp
    win_end_time = win_start_time + dt.timedelta(seconds=config.incident.time_interval)
    ix = 0
    incidents = []
    while ix < len(events):
        win_events = [event for event in events if win_start_time <= event.timestamp <= win_end_time]
        if len(win_events) < incident_threshold:
            # Not enough events in the current window to create an incident, move the window forward to the next event
            ix += 1
            win_start_time = events[ix].timestamp if ix < len(events) else win_start_time
            win_end_time = win_start_time + dt.timedelta(seconds=config.incident.time_interval)
            continue

        # Enough events in the current window to create an incident
        now = dt.datetime.now(dt.timezone.utc)
        incident = Incident(
            type=incident_type,
            fingerprint=fingerprint,
            environment=environment,
            service=service,
            events={event.id for event in win_events},
            start_time=win_start_time,
            end_time=win_end_time,
            created_at=now,
            updated_at=now,
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
        if len(events) < config.incident.fingerprint_threshold:
            # Not enough events with the same fingerprint to create an incident
            continue

        start_time, end_time = _get_time_range(events)
        time_diff = end_time - start_time
        if time_diff <= dt.timedelta(seconds=config.incident.time_interval):
            # All events with the same fingerprint occurred within the time interval, create an incident
            now = dt.datetime.now(dt.timezone.utc)
            environment = events[0].environment
            service = events[0].service
            incident = Incident(
                type=IncidentType.fingerprint,
                fingerprint=fingerprint,
                environment=environment,
                service=service,
                events={event.id for event in events},
                start_time=start_time,
                end_time=end_time,
                created_at=now,
                updated_at=now,
            )
            incidents.append(incident)
            continue

        incidents.extend(_identify_incidents_by_sliding_window(IncidentType.fingerprint, events))

    return incidents


def _get_events_from_incidents(incidents: list[Incident]) -> set[uuid.UUID]:
    """Get a set of event IDs that are part of the given incidents."""
    events = set()
    for incident in incidents:
        events.update(incident.events)

    return events


def _identify_incidents_by_environment_and_service(
    grouped_events: dict[tuple[str, str], list[NormalizedEvent]], detected_incidents: list[Incident]
) -> list[Incident]:
    """Identify potential incidents based on grouped events by environment and service,
    while filtering out events that are already part of detected incidents."""
    events_from_detected_incidents = _get_events_from_incidents(detected_incidents)
    incidents = []
    for (environment, service), events in grouped_events.items():
        # Filter out events that are already part of detected incidents
        events = [event for event in events if event.id not in events_from_detected_incidents]
        if len(events) < config.incident.service_env_threshold:
            # Not enough events with the same environment and service to create an incident
            continue

        start_time, end_time = _get_time_range(events)
        time_diff = end_time - start_time
        if time_diff <= dt.timedelta(seconds=config.incident.time_interval):
            # All events with the same environment and service occurred within the time interval, create an incident
            now = dt.datetime.now(dt.timezone.utc)
            incident = Incident(
                type=IncidentType.environment_service,
                fingerprint=None,
                environment=environment,
                service=service,
                events={event.id for event in events},
                start_time=start_time,
                end_time=end_time,
                created_at=now,
                updated_at=now,
            )
            incidents.append(incident)
            continue

        incidents.extend(_identify_incidents_by_sliding_window(IncidentType.environment_service, events))

    return incidents


def check_for_incidents(opensearch_client: OpenSearchClient, db_client: DBClient, normalized_events: list[NormalizedEvent]) -> list[Incident]:
    """Checks for potential incidents based on the normalized events and creates incidents if detected."""
    min_timestamp, max_timestamp = _get_time_range(normalized_events)
    earlier_events = opensearch_client.fetch_events_for_given_timestamp_range(
        min_timestamp - dt.timedelta(seconds=config.incident.time_interval), min_timestamp
    )
    later_events = opensearch_client.fetch_events_for_given_timestamp_range(
        max_timestamp, max_timestamp + dt.timedelta(seconds=config.incident.time_interval)
    )
    all_events = earlier_events + normalized_events + later_events

    # Drop events that are not "error" or "critical"
    all_events = [event for event in all_events if event.severity in {Severity.error, Severity.critical}]

    # Drop events that are already associated with an incident, since they have already been processed
    uuid_of_events_with_incidents = db_client.return_uuids_of_events_with_incidents(all_events)
    no_incidents_events = [event for event in all_events if event.id not in uuid_of_events_with_incidents]

    # Sort events by timestamp in ascending order
    no_incidents_events.sort(key=lambda event: event.timestamp)

    group_by_fingerprint = _group_events_by_fingerprint(no_incidents_events)
    incidents_by_fingerprint = _identify_incidents_by_fingerprint(group_by_fingerprint)

    group_by_environment_and_service = _group_events_by_environment_and_service(no_incidents_events)
    incidents_by_environment_and_service = _identify_incidents_by_environment_and_service(group_by_environment_and_service, incidents_by_fingerprint)

    return incidents_by_fingerprint + incidents_by_environment_and_service

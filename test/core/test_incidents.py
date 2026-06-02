import datetime as dt
from uuid import UUID, uuid4

import pytest

from src.core import incidents
from src.core.schemas.events import NormalizedEvent, Severity
from src.core.schemas.incidents import Incident, IncidentType

BASE_TIME = dt.datetime(2026, 6, 2, 10, 0, tzinfo=dt.timezone.utc)


class FakeOpenSearchClient:
    def __init__(self, earlier_events: list[NormalizedEvent], later_events: list[NormalizedEvent]) -> None:
        self.earlier_events = earlier_events
        self.later_events = later_events
        self.calls: list[tuple[dt.datetime, dt.datetime]] = []

    def fetch_events_for_given_timestamp_range(self, start_time: dt.datetime, end_time: dt.datetime) -> list[NormalizedEvent]:
        self.calls.append((start_time, end_time))
        if len(self.calls) == 1:
            return self.earlier_events
        return self.later_events


@pytest.fixture(autouse=True)
def incident_config(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(incidents.config.incident, "time_interval", 300)
    monkeypatch.setattr(incidents.config.incident, "fingerprint_threshold", 3)
    monkeypatch.setattr(incidents.config.incident, "service_env_threshold", 3)


def _event(
    event_id: str,
    seconds: int,
    *,
    fingerprint: str = "same-fingerprint",
    severity: Severity = Severity.error,
    environment: str = "production",
    service: str = "auth-service",
    incident_id: UUID | None = None,
) -> NormalizedEvent:
    """Helper function to create a NormalizedEvent with a specific timestamp based on the BASE_TIME."""
    timestamp = BASE_TIME + dt.timedelta(seconds=seconds)
    return NormalizedEvent(
        id=UUID(event_id),
        batch_id=None,
        service=service,
        severity=severity,
        environment=environment,
        event_type="application_log",
        message="Database query timed out after 42 ms",
        metadata={},
        timestamp=timestamp,
        published_at=timestamp + dt.timedelta(seconds=1),
        normalized_message="database query timed out after <number> ms",
        fingerprint=fingerprint,
        incident_id=incident_id,
        received_at=timestamp + dt.timedelta(seconds=2),
        updated_at=None,
    )


def test_get_time_range_returns_minimum_and_maximum_timestamps() -> None:
    """Tests that _get_time_range correctly identifies the earliest and latest timestamps from a list of events."""
    events = [
        _event("123e4567-e89b-12d3-a456-426614174001", 120),
        _event("123e4567-e89b-12d3-a456-426614174002", 0),
        _event("123e4567-e89b-12d3-a456-426614174003", 60),
    ]

    start_time, end_time = incidents._get_time_range(events)

    assert start_time == BASE_TIME
    assert end_time == BASE_TIME + dt.timedelta(seconds=120)


def test_group_events_by_fingerprint() -> None:
    """Tests that _group_events_by_fingerprint correctly groups events by their fingerprint."""
    first = _event("123e4567-e89b-12d3-a456-426614174001", 0, fingerprint="fingerprint-a")
    second = _event("123e4567-e89b-12d3-a456-426614174002", 10, fingerprint="fingerprint-b")
    third = _event("123e4567-e89b-12d3-a456-426614174003", 20, fingerprint="fingerprint-a")

    grouped = incidents._group_events_by_fingerprint([first, second, third])

    assert grouped == {
        "fingerprint-a": [first, third],
        "fingerprint-b": [second],
    }


def test_group_events_by_environment_and_service() -> None:
    """Tests that _group_events_by_environment_and_service correctly groups events by their environment and service."""
    first = _event("123e4567-e89b-12d3-a456-426614174001", 0, environment="production", service="auth-service")
    second = _event("123e4567-e89b-12d3-a456-426614174002", 10, environment="staging", service="auth-service")
    third = _event("123e4567-e89b-12d3-a456-426614174003", 20, environment="production", service="auth-service")

    grouped = incidents._group_events_by_environment_and_service([first, second, third])

    assert grouped == {
        ("production", "auth-service"): [first, third],
        ("staging", "auth-service"): [second],
    }


def test_identify_incidents_by_fingerprint_creates_incident_when_threshold_is_met() -> None:
    """Tests that _identify_incidents_by_fingerprint creates an incident when the threshold is met."""
    events = [
        _event("123e4567-e89b-12d3-a456-426614174001", 0, fingerprint="fingerprint-a"),
        _event("123e4567-e89b-12d3-a456-426614174002", 60, fingerprint="fingerprint-a"),
        _event("123e4567-e89b-12d3-a456-426614174003", 120, fingerprint="fingerprint-a"),
    ]

    detected = incidents._identify_incidents_by_fingerprint({"fingerprint-a": events})

    assert len(detected) == 1
    incident = detected[0]
    assert incident.type == IncidentType.fingerprint
    assert incident.fingerprint == "fingerprint-a"
    assert incident.environment is None
    assert incident.service is None
    assert incident.events == {event.id for event in events}
    assert incident.start_time == BASE_TIME
    assert incident.end_time == BASE_TIME + dt.timedelta(seconds=120)


def test_identify_incidents_by_environment_and_service_excludes_events_in_detected_incidents() -> None:
    """Tests that _identify_incidents_by_environment_and_service excludes events already part of detected incidents."""
    first = _event("123e4567-e89b-12d3-a456-426614174001", 0, fingerprint="fingerprint-a")
    second = _event("123e4567-e89b-12d3-a456-426614174002", 60, fingerprint="fingerprint-a")
    third = _event("123e4567-e89b-12d3-a456-426614174003", 120, fingerprint="fingerprint-b")
    fourth = _event("123e4567-e89b-12d3-a456-426614174004", 180, fingerprint="fingerprint-c")
    detected_fingerprint_incident = Incident(
        id=uuid4(),
        type=IncidentType.fingerprint,
        fingerprint="fingerprint-a",
        environment=None,
        service=None,
        events={first.id, second.id},
        start_time=first.timestamp,
        end_time=second.timestamp,
        created_at=BASE_TIME,
        updated_at=BASE_TIME,
    )

    detected = incidents._identify_incidents_by_environment_and_service(
        {("production", "auth-service"): [first, second, third, fourth]},
        [detected_fingerprint_incident],
    )

    assert len(detected) == 0


def test_check_for_incidents_fetches_neighboring_events_and_filters_processed_or_low_severity_events() -> None:
    """Tests that check_for_incidents fetches neighboring events and filters out processed or low-severity events."""
    current = _event("123e4567-e89b-12d3-a456-426614174002", 60)
    earlier = _event("123e4567-e89b-12d3-a456-426614174001", 0)
    later = _event("123e4567-e89b-12d3-a456-426614174003", 120)
    low_severity = _event("123e4567-e89b-12d3-a456-426614174004", 130, severity=Severity.info)
    already_processed = _event("123e4567-e89b-12d3-a456-426614174005", 140, incident_id=uuid4())
    opensearch_client = FakeOpenSearchClient(
        earlier_events=[earlier],
        later_events=[later, low_severity, already_processed],
    )

    detected = incidents.check_for_incidents(opensearch_client, [current])

    assert opensearch_client.calls == [
        (current.timestamp - dt.timedelta(seconds=300), current.timestamp),
        (current.timestamp, current.timestamp + dt.timedelta(seconds=300)),
    ]
    assert len(detected) == 1
    assert detected[0].type == IncidentType.fingerprint
    assert detected[0].events == {earlier.id, current.id, later.id}

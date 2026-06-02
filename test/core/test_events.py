import datetime as dt
import hashlib
from uuid import UUID

import pytest
from pydantic import ValidationError

from src.core.events import _create_fingerprint, _normalize_event_message, normalize_event
from src.core.schemas.events import Event, Severity


def _event_payload() -> dict:
    return {
        "id": "123e4567-e89b-12d3-a456-426614174000",
        "batch_id": "123e4567-e89b-12d3-a456-426614174001",
        "service": " Auth-Service ",
        "severity": " ERROR ",
        "environment": " Production ",
        "event_type": " Application_Log ",
        "message": "User john@example.com failed login from 192.168.1.10 in 42 ms",
        "metadata": {"attempt": 1},
        "timestamp": "2026-06-02T10:00:00Z",
        "published_at": "2026-06-02T10:00:05Z",
    }


def test_normalize_event_message_replaces_volatile_values_and_lowercases() -> None:
    """Test that _normalize_event_message correctly replaces volatile values with placeholders and lowercases the message."""
    message = (
        " User john@example.com opened https://example.com/orders/123 "
        "with id 123e4567-e89b-12d3-a456-426614174000 from 192.168.1.10 "
        "using token eyJabc.def.ghi at /var/log/app.log in 42.5 ms "
    )

    normalized_message = _normalize_event_message(message)

    assert normalized_message == ("user <email> opened <url> with id <uuid> from <ip> using token <token> at <path> in <number> ms")


def test_create_fingerprint_is_sha256_of_normalized_event_identity() -> None:
    """Test that _create_fingerprint generates a SHA-256 hash of the normalized event identity components."""
    event = Event.model_validate(_event_payload())
    normalized_message = "user <email> failed login from <ip> in <number> ms"
    expected_input = "|".join(
        [
            "auth-service",
            "error",
            normalized_message,
            "production",
            "application_log",
        ]
    )

    fingerprint = _create_fingerprint(event, normalized_message)

    assert fingerprint == hashlib.sha256(expected_input.encode()).hexdigest()


def test_normalize_event_validates_and_enriches_payload() -> None:
    """Test that normalize_event validates and enriches the event payload."""
    received_at = dt.datetime(2026, 6, 2, 10, 1, tzinfo=dt.timezone.utc)

    normalized_event = normalize_event(_event_payload(), received_at)

    assert normalized_event.id == UUID("123e4567-e89b-12d3-a456-426614174000")
    assert normalized_event.batch_id == UUID("123e4567-e89b-12d3-a456-426614174001")
    assert normalized_event.service == "auth-service"
    assert normalized_event.severity == Severity.error
    assert normalized_event.environment == "production"
    assert normalized_event.event_type == "application_log"
    assert normalized_event.normalized_message == "user <email> failed login from <ip> in <number> ms"
    assert normalized_event.received_at == received_at
    assert normalized_event.incident_id is None
    assert normalized_event.updated_at is None


def test_normalize_event_uses_same_fingerprint_for_equivalent_messages() -> None:
    """Test that normalize_event generates the same fingerprint for equivalent messages."""
    received_at = dt.datetime(2026, 6, 2, 10, 1, tzinfo=dt.timezone.utc)
    first_payload = _event_payload()
    second_payload = {
        **_event_payload(),
        "id": "123e4567-e89b-12d3-a456-426614174002",
        "message": "User jane@example.org failed login from 10.0.0.1 in 900 ms",
    }

    first_event = normalize_event(first_payload, received_at)
    second_event = normalize_event(second_payload, received_at)

    assert first_event.normalized_message == second_event.normalized_message
    assert first_event.fingerprint == second_event.fingerprint


def test_normalize_event_raises_validation_error_for_invalid_payload() -> None:
    """Test that normalize_event raises a ValidationError for invalid payloads."""
    payload = _event_payload()
    payload["message"] = ""

    with pytest.raises(ValidationError):
        normalize_event(payload, dt.datetime.now(dt.timezone.utc))

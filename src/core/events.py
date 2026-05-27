import datetime as dt
import hashlib

from src.core.normalization_expressions import NORMALIZATION_RULES
from src.core.schemas.events import Event, NormalizedEvent


def _normalize_event_message(event_msg: str) -> str:
    """Normalize the event message by applying regex patterns to replace volatile information with placeholders."""
    normalized_msg = event_msg.strip()
    for pattern, replacement in NORMALIZATION_RULES:
        normalized_msg = pattern.sub(replacement, normalized_msg)

    return normalized_msg.lower()


def _create_fingerprint(event: Event, normalized_message: str) -> str:
    """Create a unique fingerprint for the event based on its normalized attributes."""
    fingerprint_input = "|".join([event.service, event.severity, normalized_message, event.environment, event.event_type])
    return hashlib.sha256(fingerprint_input.encode()).hexdigest()


def normalize_event(event: Event, received_at: dt.datetime) -> NormalizedEvent:
    """Normalize an event by creating a NormalizedEvent instance with a normalized message and fingerprint."""
    normalized_message = _normalize_event_message(event.message)
    fingerprint = _create_fingerprint(event, normalized_message)

    return NormalizedEvent(
        **event.model_dump(),
        normalized_message=normalized_message,
        fingerprint=fingerprint,
        received_at=received_at,
    )

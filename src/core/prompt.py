from src.core.events import group_normalized_messages
from src.core.schemas.events import NormalizedEvent
from src.core.schemas.incidents import IncidentGet, IncidentType


def generate_prompt(incident: IncidentGet, events: list[NormalizedEvent]) -> str:
    """Generates a prompt for LLM based on the incident and its related events."""
    if incident.type == IncidentType.fingerprint:
        events_text = f"{events[0].normalized_message} - (occurred {len(events)} times)"
    else:
        grouped_events = group_normalized_messages(events)
        events_text = "\n\t".join([f"{messages[0]} - (occurred {len(messages)} times)" for messages in grouped_events.values()])

    incident_text = f"""Here are the incident details
    
        Environment: {incident.environment}
        Service: {incident.service}
        Start Time: {incident.start_time}
        End Time: {incident.end_time}
        Normalized Log Messages (sensitive information redacted):\n
        {events_text}
    """
    prompt = f"""
    You are a Site Reliability Engineer.

    Analyze the following incident and provide:

    1. Summary
    2. Most likely root cause
    3. Confidence (low, medium, high)
    4. List of recommended actions (up to 5 recommendations)

    {incident_text}
    """
    return prompt.strip()

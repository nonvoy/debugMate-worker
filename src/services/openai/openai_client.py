from functools import lru_cache

from openai import OpenAI

from src.config.basic_config import get_config
from src.core.prompt import generate_prompt
from src.core.schemas.events import NormalizedEvent
from src.core.schemas.incidents import IncidentAnalysis, IncidentGet

config = get_config()


class OpenAIClient:
    """Client for interacting with OpenAI API to analyze incidents."""

    def __init__(self):
        self._client = OpenAI(api_key=config.openai.api_key)

    def analyze_incident(self, incident: IncidentGet, events: list[NormalizedEvent]) -> IncidentAnalysis:
        """Sends the incident data to OpenAI for analysis and returns the results."""
        prompt_text = generate_prompt(incident, events)
        return self._client.responses.create(model=config.openai.model_name, input=prompt_text, text_format=IncidentAnalysis.model_json_schema())


@lru_cache
def get_openai_client() -> OpenAIClient:
    return OpenAIClient()

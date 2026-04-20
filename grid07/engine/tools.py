import logging

from langchain.tools import tool

logger = logging.getLogger(__name__)


def _lookup_headline(query: str) -> str:
    lowered = query.lower()
    if "crypto" in lowered or "bitcoin" in lowered:
        return "Bitcoin hits new all-time high amid regulatory ETF approvals"
    if "ai" in lowered or "model" in lowered or "openai" in lowered:
        return "OpenAI's GPT-5 triggers mass layoffs in junior dev roles, say recruiters"
    if "market" in lowered or "fed" in lowered or "rate" in lowered:
        return "Fed signals two more rate cuts; S&P surges 2.3% in after-hours"
    if "elon" in lowered or "space" in lowered or "tesla" in lowered:
        return "SpaceX Starship completes orbital loop; Musk calls it 'civilisation-defining'"
    if "privacy" in lowered or "surveillance" in lowered:
        return "EU passes landmark AI surveillance ban; US tech stocks dip"
    return "Global markets show mixed signals as geopolitical tensions rise"


@tool
def mock_searxng_search(query: str) -> str:
    """Return a mocked headline for a search query."""
    # mock for searxng — replace with real HTTP call in prod
    answer = _lookup_headline(query)
    logger.info(f"mock_searxng_search('{query}') -> {answer}")
    return answer

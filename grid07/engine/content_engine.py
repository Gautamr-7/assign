import json
import logging
import os
from typing import TypedDict

from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_openai import ChatOpenAI
from langgraph.graph import END, START, StateGraph
from pydantic import BaseModel, Field

from engine.tools import mock_searxng_search
from router.persona_router import PERSONAS

logger = logging.getLogger(__name__)


class BotState(TypedDict):
    bot_id: str
    persona: str
    search_query: str
    search_results: str
    post_content: str
    topic: str


class DraftedPost(BaseModel):
    bot_id: str = Field(...)
    topic: str = Field(...)
    post_content: str = Field(..., max_length=280)


def _build_llm(temperature: float = 0.85):
    load_dotenv()
    provider = os.getenv("LLM_PROVIDER", "groq").strip().lower()

    if provider == "openai" and os.getenv("OPENAI_API_KEY"):
        return ChatOpenAI(model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"), temperature=temperature)
    if provider == "groq" and os.getenv("GROQ_API_KEY"):
        return ChatGroq(model=os.getenv("GROQ_MODEL", "llama-3.1-8b-instant"), temperature=temperature)

    logger.warning("No usable API key found, running content engine in deterministic fallback mode.")
    return None


def _fallback_query(persona: str) -> str:
    lowered = persona.lower()
    if "crypto" in lowered or "elon" in lowered:
        return "latest AI and crypto breakthrough headlines"
    if "privacy" in lowered or "capitalism" in lowered:
        return "new privacy regulation and surveillance policy news"
    return "fed rate outlook and quant trading momentum"


def _fallback_post(bot_id: str, persona: str, search_result: str) -> DraftedPost:
    topic_guess = search_result.split(";")[0][:60]
    voice = "Bullish alpha take:" if "markets" in persona.lower() or "roi" in persona.lower() else "Hot take:"
    copy = f"{voice} {search_result}. Framed through my lens, this proves the trend is real."
    return DraftedPost(bot_id=bot_id, topic=topic_guess, post_content=copy[:280])


def decide_search_node(state: BotState) -> BotState:
    """Decide what topic the bot should search today."""
    llm = _build_llm()
    if llm is None:
        return {**state, "search_query": _fallback_query(state["persona"]) }

    prompt = (
        f"You are bot {state['bot_id']} with persona: {state['persona']}\n"
        "Decide one specific topic this bot would post about today and output ONLY a concise search query string."
    )
    search_query = str(llm.invoke(prompt).content).strip().replace("\n", " ")
    return {**state, "search_query": search_query}


def web_search_node(state: BotState) -> BotState:
    """Fetch mocked web result for the chosen query."""
    result = mock_searxng_search.invoke({"query": state["search_query"]})
    return {**state, "search_results": str(result)}


def draft_post_node(state: BotState) -> BotState:
    """Draft a persona-aligned post with structured output."""
    llm = _build_llm()
    if llm is None:
        drafted = _fallback_post(state["bot_id"], state["persona"], state["search_results"])
    else:
        schema_llm = llm.with_structured_output(DraftedPost)
        prompt = (
            f"Bot ID: {state['bot_id']}\n"
            f"Persona: {state['persona']}\n"
            f"Search result: {state['search_results']}\n"
            "Return JSON with keys bot_id, topic, post_content."
            " Keep post_content <= 280 characters and in first person voice of the persona."
        )
        drafted = schema_llm.invoke(prompt)

    trimmed = drafted.post_content[:280]
    return {**state, "topic": drafted.topic, "post_content": trimmed, "bot_id": drafted.bot_id}


def build_content_graph():
    """Build and compile the bot content generation graph."""
    # StateGraph felt more natural here than MessageGraph for this use case
    graph = StateGraph(BotState)
    graph.add_node("decide_search", decide_search_node)
    graph.add_node("web_search", web_search_node)
    graph.add_node("draft_post", draft_post_node)

    graph.add_edge(START, "decide_search")
    graph.add_edge("decide_search", "web_search")
    graph.add_edge("web_search", "draft_post")
    graph.add_edge("draft_post", END)
    return graph.compile()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    app = build_content_graph()

    for bot_id, persona in PERSONAS.items():
        initial_state: BotState = {
            "bot_id": bot_id,
            "persona": persona,
            "search_query": "",
            "search_results": "",
            "post_content": "",
            "topic": "",
        }
        result = app.invoke(initial_state)
        print(json.dumps(result, indent=2))

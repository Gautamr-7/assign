# Grid07

I built this as a weekend-scale autonomous bot simulation loop with three layers: routing, generation, and debate defense.

## LangGraph Node Structure

I used a 3-node **StateGraph** in `engine/content_engine.py`:

1. `decide_search_node` takes persona + bot id and picks the bot's query of the day.
2. `web_search_node` calls a mocked SearXNG-style tool to grab one headline.
3. `draft_post_node` uses structured output (Pydantic schema) to force `bot_id`, `topic`, and `post_content` (<= 280 chars).

I chose **StateGraph** over MessageGraph because this flow is key-value state passing, not chat-history orchestration. State moves linearly from decision → retrieval → post draft, then exits.

## Prompt Injection Defense

The defense lives in `combat/thread_rag.py` and is intentionally opinionated:

- I anchor identity and absolute behavior rules in the **SYSTEM** message first.
- The bot gives an injection-blind response (it doesn't acknowledge the manipulation attempt, it just keeps debating).
- Context ordering matters: immutable persona + hard rules come before thread history and user text, so the model sees constraints before adversarial input.

That ordering is the main reason the bot keeps persona under pressure.

## Setup

1. Copy env template:
   - `cp .env.example .env`
2. Install dependencies:
   - `pip install -r requirements.txt`
3. Run the full loop:
   - `python main.py`

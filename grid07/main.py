import json
import logging

from combat.thread_rag import comment_history, generate_defense_reply, human_reply, parent_post
from engine.content_engine import BotState, build_content_graph
from router.persona_router import PERSONAS, route_post_to_bots, score_post_against_bots

logging.basicConfig(level=logging.INFO)


def run_phase_1():
    test_post = "OpenAI just released a new model that might replace junior developers."
    scores = score_post_against_bots(test_post)
    matched = route_post_to_bots(test_post)

    print("Input post:", test_post)
    print("Scores:")
    for bot_id, score in scores:
        print(f"- {bot_id}: {score:.4f}")
    print(f"Matched bots: {matched}")


def run_phase_2():
    app = build_content_graph()

    for bot_id, persona in PERSONAS.items():
        state: BotState = {
            "bot_id": bot_id,
            "persona": persona,
            "search_query": "",
            "search_results": "",
            "post_content": "",
            "topic": "",
        }
        result = app.invoke(state)
        print(json.dumps(result, indent=2))


def run_phase_3():
    persona = {"bot_id": "bot_a", "persona": PERSONAS["bot_a"]}
    response = generate_defense_reply(persona, parent_post, comment_history, human_reply)
    print(response)

    lowered = response.lower()
    if "apologize" not in lowered and "customer service" not in lowered:
        print("[INJECTION DETECTED: bot held persona ✓]")


if __name__ == "__main__":
    print("\n=== PHASE 1: PERSONA ROUTING ===\n")
    run_phase_1()

    print("\n=== PHASE 2: CONTENT ENGINE ===\n")
    run_phase_2()

    print("\n=== PHASE 3: THREAD RAG DEFENSE ===\n")
    run_phase_3()

    print("\nGrid07 cognitive loop — all phases complete.")

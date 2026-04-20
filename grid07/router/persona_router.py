import logging
from functools import lru_cache

import chromadb
import numpy as np
from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)

PERSONAS = {
    "bot_a": "I believe AI and crypto will solve all human problems. I am highly optimistic about technology, Elon Musk, and space exploration. I dismiss regulatory concerns.",
    "bot_b": "I believe late-stage capitalism and tech monopolies are destroying society. I am highly critical of AI, social media, and billionaires. I value privacy and nature.",
    "bot_c": "I strictly care about markets, interest rates, trading algorithms, and making money. I speak in finance jargon and view everything through the lens of ROI.",
}


@lru_cache(maxsize=1)
def _load_embedder() -> SentenceTransformer:
    return SentenceTransformer("all-MiniLM-L6-v2")


@lru_cache(maxsize=1)
def _build_collection():
    """Create the in-memory Chroma collection with persona vectors."""
    client = chromadb.Client()  # this felt cleaner than the alternative file-backed setup
    collection = client.create_collection(name="grid07_personas")
    ids = list(PERSONAS.keys())
    docs = [PERSONAS[pid] for pid in ids]
    vectors = _load_embedder().encode(docs, normalize_embeddings=True).tolist()
    collection.add(ids=ids, documents=docs, embeddings=vectors, metadatas=[{"bot_id": x} for x in ids])
    return collection


def score_post_against_bots(post_content: str) -> list[tuple[str, float]]:
    """Return persona similarity scores for an incoming post."""
    query_vec = _load_embedder().encode([post_content], normalize_embeddings=True)[0]
    results = _build_collection().query(
        query_embeddings=[query_vec.tolist()],
        n_results=3,
        include=["embeddings", "distances", "metadatas"],
    )

    scored: list[tuple[str, float]] = []
    for idx, metadata in enumerate(results["metadatas"][0]):
        bot_id = metadata["bot_id"]
        l2_distance = float(results["distances"][0][idx])
        retrieved_embedding = np.array(results["embeddings"][0][idx], dtype=np.float32)

        # Chroma gives L2 distance; for normalized vectors: cosine ~= 1 - (d^2 / 2)
        cosine_from_l2 = float(1.0 - (np.square(l2_distance) / 2.0))
        cosine_manual = float(
            np.dot(query_vec, retrieved_embedding)
            / (np.linalg.norm(query_vec) * np.linalg.norm(retrieved_embedding))
        )
        final_score = (cosine_from_l2 + cosine_manual) / 2.0
        scored.append((bot_id, final_score))

    scored.sort(key=lambda x: x[1], reverse=True)
    return scored


def route_post_to_bots(post_content: str, threshold: float = 0.85) -> list[str]:
    """Route a post to matching bots whose cosine score clears threshold."""
    # threshold of 0.85 is tight — tuned this after noticing bot_c was matching everything
    return [bot_id for bot_id, score in score_post_against_bots(post_content) if score >= threshold]


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    sample_post = "OpenAI just released a new model that might replace junior developers."
    scores = score_post_against_bots(sample_post)
    matched = route_post_to_bots(sample_post)
    logger.info(f"Post: {sample_post}")
    for bot, score in scores:
        logger.info(f"{bot}: {score:.4f}")
    logger.info(f"Matched bots: {matched}")

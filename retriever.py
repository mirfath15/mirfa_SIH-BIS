"""
Hybrid retrieval: semantic similarity (ChromaDB embeddings) merged with
keyword/BM25-style matching. Combining both matters for a standards
assistant because:
  - semantic search finds relevant chunks even when the user's wording
    differs from the standard's wording ("is my toy safe" -> toy safety IS),
  - keyword search reliably catches exact identifiers embeddings can blur,
    like "IS 10500" or "925 silver".
"""

import re
from typing import List, Tuple

import config
from knowledge_base import Chunk, get_chroma_collection

# Define common English stop words to filter out noise
STOP_WORDS = {
    "i", "me", "my", "myself", "we", "our", "ours", "ourselves", "you", "your",
    "yours", "yourself", "yourselves", "he", "him", "his", "himself", "she",
    "her", "hers", "herself", "it", "its", "itself", "they", "them", "their",
    "theirs", "themselves", "what", "which", "who", "whom", "this", "that",
    "these", "those", "am", "is", "are", "was", "were", "be", "been", "being",
    "have", "has", "had", "having", "do", "does", "did", "doing", "a", "an",
    "the", "and", "but", "if", "or", "because", "as", "until", "while", "of",
    "at", "by", "for", "with", "about", "against", "between", "into", "through",
    "during", "before", "after", "above", "below", "to", "from", "up", "down",
    "in", "out", "on", "off", "over", "under", "again", "further", "then",
    "once", "here", "there", "when", "where", "why", "how", "all", "any",
    "both", "each", "few", "more", "most", "other", "some", "such", "no",
    "nor", "not", "only", "own", "same", "so", "than", "too", "very", "s",
    "t", "can", "will", "just", "don", "should", "now",
}

STANDARD_NUMBER_RE = re.compile(r"\bIS[\s\-]?\d{2,6}\b", re.IGNORECASE)


def tokenize(text: str) -> List[str]:
    tokens = re.findall(r"[a-z0-9]+", text.lower())
    return [t for t in tokens if t not in STOP_WORDS and len(t) > 1]


def _keyword_score(query_tokens: List[str], chunk: Chunk) -> float:
    """Raw (unnormalized) keyword score for one chunk."""
    score = 0.0
    haystack_tokens = set(tokenize(chunk.title + " " + chunk.text + " " + chunk.service))
    keyword_tokens = set()
    for kw in chunk.keywords:
        keyword_tokens.update(tokenize(kw))

    for tok in query_tokens:
        if tok in keyword_tokens:
            score += 3.0  # explicit keyword match
        elif tok in haystack_tokens:
            score += 1.0  # general text match
    return score


def keyword_search(query: str, chunks_by_id: dict, top_k: int = config.TOP_K_KEYWORD) -> List[Tuple[str, float]]:
    """Return [(chunk_id, normalized_score_0_to_1), ...], best first."""
    query_tokens = tokenize(query)
    if not query_tokens:
        return []

    scored = [(cid, _keyword_score(query_tokens, c)) for cid, c in chunks_by_id.items()]
    scored = [pair for pair in scored if pair[1] > 0]
    if not scored:
        return []

    max_score = max(s for _, s in scored) or 1.0
    scored = [(cid, s / max_score) for cid, s in scored]
    scored.sort(key=lambda pair: pair[1], reverse=True)
    return scored[:top_k]


def semantic_search(query: str, top_k: int = config.TOP_K_SEMANTIC) -> List[Tuple[str, float]]:
    """Return [(chunk_id, normalized_score_0_to_1), ...] from ChromaDB, best first."""
    collection, _ = get_chroma_collection()
    if collection.count() == 0:
        return []

    result = collection.query(query_texts=[query], n_results=min(top_k, collection.count()))
    ids = result.get("ids", [[]])[0]
    distances = result.get("distances", [[]])[0]

    scored = []
    for cid, dist in zip(ids, distances):
        # Chroma's default embedding space uses squared-L2 distance; convert
        # to a similarity-like score in roughly [0, 1] (closer to 1 = better).
        similarity = 1.0 / (1.0 + dist)
        scored.append((cid, similarity))
    return scored


def hybrid_merge(
    semantic_results: List[Tuple[str, float]],
    keyword_results: List[Tuple[str, float]],
    alpha: float = config.SEMANTIC_WEIGHT,
) -> List[Tuple[str, float]]:
    """Weighted merge of two ranked (chunk_id, score) lists by chunk_id."""
    combined = {}
    for cid, score in semantic_results:
        combined[cid] = combined.get(cid, 0.0) + alpha * score
    for cid, score in keyword_results:
        combined[cid] = combined.get(cid, 0.0) + (1 - alpha) * score

    merged = sorted(combined.items(), key=lambda pair: pair[1], reverse=True)
    return merged


def retrieve(query: str, top_k: int = config.FINAL_TOP_K) -> List[Tuple[float, Chunk]]:
    """Public entry point: returns [(score, Chunk), ...] best first.

    An explicit standard number in the query (e.g. "IS 1417") is boosted so
    an exact identifier match always wins over a loosely-related semantic
    match - important because getting the standard number right is the
    whole point of this assistant.
    """
    if not query or not query.strip():
        return []

    _, chunks_by_id = get_chroma_collection()

    semantic_results = semantic_search(query)
    keyword_results = keyword_search(query, chunks_by_id)
    merged = hybrid_merge(semantic_results, keyword_results)

    explicit_standard = STANDARD_NUMBER_RE.search(query)
    if explicit_standard:
        needle = explicit_standard.group(0).replace(" ", "").replace("-", "").lower()
        boosted = []
        for cid, score in merged:
            chunk = chunks_by_id.get(cid)
            haystack = (chunk.standard if chunk else "").replace(" ", "").replace("-", "").lower()
            boosted.append((cid, score + (1.0 if needle in haystack else 0.0)))
        merged = sorted(boosted, key=lambda pair: pair[1], reverse=True)

    results = [(score, chunks_by_id[cid]) for cid, score in merged if cid in chunks_by_id]
    return results[:top_k]

"""
Connects hybrid retrieval to Gemini generation, and is the ONLY place that
talks to the Gemini API. Centralizing this fixed the original bug where
app.py and compliance_engine.py each hardcoded a different (and in one
case invalid) model name via two different SDKs.
"""

import os
import time
from dataclasses import dataclass
from typing import List, Optional

import streamlit as st

import config
import prompts
from knowledge_base import Chunk
from retriever import retrieve

# Gemini occasionally returns transient errors when its servers are under
# heavy load (503 UNAVAILABLE) or when a rate limit is briefly hit (429).
# Both are worth a short automatic retry before giving up.
RETRYABLE_MARKERS = ("503", "UNAVAILABLE", "429", "RESOURCE_EXHAUSTED")
MAX_RETRIES = 3
RETRY_BACKOFF_SECONDS = 2  # doubles each retry: 2s, 4s, 8s


@dataclass
class RagResponse:
    answer: str
    sources: List[Chunk]
    used_fallback: bool  # True when we skipped Gemini due to weak/no context
    error: Optional[str] = None


def _get_api_key() -> Optional[str]:
    try:
        if "GOOGLE_API_KEY" in st.secrets:
            return st.secrets["GOOGLE_API_KEY"]
    except Exception:
        pass
    return os.getenv("GOOGLE_API_KEY")


@st.cache_resource(show_spinner=False)
def _get_client():
    from google import genai

    api_key = _get_api_key()
    if not api_key:
        return None
    return genai.Client(api_key=api_key)


def _call_gemini(prompt: str) -> str:
    client = _get_client()
    if client is None:
        raise RuntimeError(
            "GOOGLE_API_KEY not found. Add it to .streamlit/secrets.toml "
            "(GOOGLE_API_KEY = \"...\") or set it as an environment variable."
        )

    last_error = None
    for attempt in range(MAX_RETRIES):
        try:
            response = client.models.generate_content(
                model=config.GEMINI_MODEL,
                contents=prompt,
                config={
                    "temperature": config.GEMINI_TEMPERATURE,
                    "max_output_tokens": config.GEMINI_MAX_OUTPUT_TOKENS,
                },
            )
            return response.text
        except Exception as exc:  # noqa: BLE001
            last_error = exc
            is_retryable = any(marker in str(exc) for marker in RETRYABLE_MARKERS)
            if is_retryable and attempt < MAX_RETRIES - 1:
                time.sleep(RETRY_BACKOFF_SECONDS * (2 ** attempt))
                continue
            raise

    raise last_error  # pragma: no cover - loop always returns or raises above


def _run(query: str, prompt_builder) -> RagResponse:
    results = retrieve(query, top_k=config.FINAL_TOP_K)

    if not results or results[0][0] < config.MIN_RELEVANCE_SCORE:
        return RagResponse(
            answer=(
                "I couldn't find a confident match for that in the BIS knowledge "
                "base. Could you share more detail (product type, material, or "
                "the standard number if you know it)? You can also check "
                "https://www.bis.gov.in for the authoritative source."
            ),
            sources=[],
            used_fallback=True,
        )

    chunks = [chunk for _score, chunk in results]
    prompt = prompt_builder(query, chunks)

    try:
        answer = _call_gemini(prompt)
    except Exception as exc:  # noqa: BLE001 - surfaced to the user, not silenced
        is_retryable = any(marker in str(exc) for marker in RETRYABLE_MARKERS)
        if is_retryable:
            friendly = (
                "Gemini's servers are temporarily overloaded (this is on "
                "Google's side, not the BIS knowledge base). I retried a few "
                "times automatically - please try asking again in a moment."
            )
        else:
            friendly = f"Sorry, I hit an error generating a response: {exc}"
        return RagResponse(
            answer=friendly,
            sources=chunks,
            used_fallback=False,
            error=str(exc),
        )

    return RagResponse(answer=answer, sources=chunks, used_fallback=False)


def generate_answer(query: str) -> RagResponse:
    """Standard question-answering mode."""
    return _run(query, prompts.build_rag_prompt)


def generate_compliance_check(product_description: str) -> RagResponse:
    """Compliance-check mode: does the described product meet the standard?"""
    return _run(product_description, prompts.build_compliance_prompt)


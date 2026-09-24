"""
Central configuration for BIS Saarthi.

Keeping every model name, path, and tunable constant in one place makes it
easy to upgrade the Gemini model later without hunting through every file
(this is exactly what broke the original demo: an invalid model string
"gemini-3.6-flash" was hardcoded inside app.py and had no fallback).
"""

import os

# ---------------------------------------------------------------------------
# Gemini model configuration
# ---------------------------------------------------------------------------
# "gemini-flash-latest" is a Google-managed alias that always points at the
# current recommended fast Gemini model, so this stays correct as Google
# ships new versions. If you need a pinned/stable model for a demo/judging
# day, set GEMINI_MODEL below to a fixed name (e.g. "gemini-2.5-flash").
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.6-flash")

# Low temperature keeps answers factual/consistent instead of creative -
# important for a standards-compliance assistant.
GEMINI_TEMPERATURE = 0.2
GEMINI_MAX_OUTPUT_TOKENS = 1024

# ---------------------------------------------------------------------------
# Retrieval configuration
# ---------------------------------------------------------------------------
CHROMA_DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "chroma_db")
COLLECTION_NAME = "bis_saarthi_chunks"

# How many candidates each retrieval method pulls before merging.
TOP_K_SEMANTIC = 5
TOP_K_KEYWORD = 5
# How many merged chunks are finally handed to Gemini as context.
FINAL_TOP_K = 3

# Weight given to semantic (embedding) similarity vs keyword score when
# merging the two ranked lists. 0.6 means "trust meaning slightly more than
# exact wording", which suits natural-language user questions.
SEMANTIC_WEIGHT = 0.6

# If the best merged result scores below this, we tell the user we don't
# have a confident match instead of forcing Gemini to answer from weak/no
# context (this is what stops the assistant from hallucinating clauses).
MIN_RELEVANCE_SCORE = 0.15

# ---------------------------------------------------------------------------
# PDF ingestion (optional - the app ships with a curated seed knowledge base
# in knowledge_base.py so it works out of the box; drop official BIS PDFs
# into data/raw_pdfs/ to extend the knowledge base with real documents).
# ---------------------------------------------------------------------------
DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
RAW_PDF_DIR = os.path.join(DATA_DIR, "raw_pdfs")
PDF_CHUNK_SIZE = 900          # approx characters per chunk
PDF_CHUNK_OVERLAP = 150

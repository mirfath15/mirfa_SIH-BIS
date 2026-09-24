# BIS Saarthi

An AI-powered assistant for Indian Standards (BIS) information — hallmarking,
product certification, testing, and licensing — built with Streamlit, hybrid
retrieval (ChromaDB + keyword search), and Google Gemini for grounded
generation.

## What was fixed / upgraded from the original demo

**Bugs (why it was erroring):**
- `app.py` called Gemini with `model="gemini-3.6-flash"`, which is not a
  valid model name — every request failed. The model name is now centralized
  in `config.py` and defaults to Google's `gemini-flash-latest` alias.
- `compliance_engine.py` used a second, inconsistent SDK/model
  (`langchain-google-genai`, `gemini-1.5-flash`) and was never even imported
  by `app.py` — it was dead code with its own separate bug. It has been
  removed; its behavior now lives in `rag_pipeline.py` / `prompts.py`.
- `requirements.txt` listed `langchain*` packages the working code path
  didn't use, and was missing `google-genai`, `chromadb`, and `pymupdf`,
  which the code (now) actually imports.
- No handling for a missing/invalid API key beyond a generic string — errors
  are now caught and surfaced clearly instead of crashing the chat.

**Upgrades (to match the original problem statement):**
- Real **PDF ingestion pipeline** (`knowledge_base.py`): drop official BIS
  PDFs into `data/raw_pdfs/` and they are extracted (PyMuPDF), cleaned,
  chunked along clause boundaries, tagged with standard number/clause/page
  metadata, and merged with the curated seed knowledge base.
- **ChromaDB** persistent vector store, embedding every chunk automatically
  (`get_chroma_collection` in `knowledge_base.py`).
- **Hybrid retrieval** (`retriever.py`): semantic similarity from ChromaDB
  merged with keyword/exact-match scoring, with an extra boost when the
  user's question names an explicit standard number (e.g. "IS 1417").
- **Strict grounding prompts** (`prompts.py`): Gemini is instructed to
  answer only from retrieved context, never invent a standard/clause number,
  and explicitly say when information is insufficient.
- **`rag_pipeline.py`**: the single place that talks to Gemini. It skips the
  API call entirely (and returns a clear "not confident" message) when
  retrieval quality is below `MIN_RELEVANCE_SCORE`, and always attaches the
  sources it actually retrieved rather than trusting the model's self-report.
- **`app.py`**: now a thin UI layer over `rag_pipeline.py`, with a mode
  switch for plain Q&A vs. a product-compliance check, and a visible
  "Sources" panel under every answer.

## Project structure

```
SIH_BIS_app/
├── app.py              # Streamlit UI
├── config.py            # Model name, retrieval weights, paths — edit here first
├── knowledge_base.py    # Curated seed data + PDF ingestion + ChromaDB storage
├── retriever.py         # Hybrid semantic + keyword retrieval
├── rag_pipeline.py       # Retrieval -> Gemini -> grounded answer + sources
├── prompts.py            # Strict grounding system prompt
├── data/raw_pdfs/         # Drop official BIS PDFs here (optional)
├── chroma_db/              # Auto-created persistent vector store
├── .streamlit/
│   └── secrets.toml.example
└── requirements.txt
```

## Setup

```bash
pip install -r requirements.txt
```

1. Copy `.streamlit/secrets.toml.example` to `.streamlit/secrets.toml` and
   add your Gemini API key:
   ```toml
   GOOGLE_API_KEY = "your-gemini-api-key-here"
   ```
2. (Optional) Add official BIS standard PDFs to `data/raw_pdfs/` to extend
   the knowledge base beyond the built-in curated demo set.
3. Run the app:
   ```bash
   streamlit run app.py
   ```

The first run builds the ChromaDB index (embeds every chunk) and caches it,
so subsequent runs start instantly. If you add new PDFs later, just restart
the app — ingestion is idempotent and only embeds new chunks.

## Notes

- Retrieval works even without a Gemini API key (it uses Chroma's bundled
  local embedding model). Only the final answer-generation step needs the
  key — until it's set, the app clearly reports the missing-key error
  instead of crashing.
- `config.GEMINI_MODEL` defaults to Google's `gemini-flash-latest` alias so
  it keeps working as Google rotates model versions. Pin it to a fixed model
  name (e.g. `gemini-2.5-flash`) if you need a stable target for a demo day.

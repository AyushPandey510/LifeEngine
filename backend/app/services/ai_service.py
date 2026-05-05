"""
AI service using Groq (OpenAI-compatible API)

- Chat completions via Groq
- Streaming support
- Embeddings via OpenAI (optional)
- Safe fallback for development
- Smart document context injection (relevance-based)
"""

import hashlib
import json
import re
from typing import Any, AsyncIterator, Dict, List, Tuple

import httpx
import structlog

from app.core.config import settings

logger = structlog.get_logger()

# =========================
# CONFIG
# =========================

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"

_openai_client = None


def _get_openai_client():
    global _openai_client
    if _openai_client is None:
        from openai import AsyncOpenAI
        _openai_client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
    return _openai_client


# =========================
# UTIL
# =========================

def _sanitize_messages(messages: List[Dict[str, str]]) -> List[Dict[str, str]]:
    sanitized = []
    for m in messages:
        role = m.get("role", "user")
        content = m.get("content", "")
        if role in {"system", "user", "assistant"} and content:
            sanitized.append({"role": role, "content": content})
    return sanitized


# =========================
# DOCUMENT RELEVANCE
# =========================

# Queries that clearly relate to personal documents but may not share
# exact words with the document content. Grouped by intent.
_INTENT_TRIGGERS: Dict[str, List[str]] = {
    "skills":          ["skill", "skills", "know", "good at", "tech stack", "tools", "expertise", "proficient", "capable"],
    "experience":      ["experience", "worked", "work", "job", "career", "history", "background", "employed", "role", "position"],
    "education":       ["education", "degree", "studied", "university", "college", "school", "qualification", "academic"],
    "certifications":  ["certif", "certified", "certificate", "license", "badge", "credential"],
    "projects":        ["project", "built", "created", "developed", "portfolio", "made", "side project"],
    "resume":          ["resume", "cv", "cover letter", "application", "applying", "hire", "hiring", "interview"],
    "summary":         ["who am i", "about me", "my profile", "tell me about myself", "summarize me", "my background"],
}


def _score_relevance(query: str, document) -> float:
    """
    Relevance score between user query and a document (0.0 – 1.0).

    Two-pass approach:
      1. Intent triggers  — query contains career/profile intent words that
                            map to document sections (skills, experience, etc.)
      2. Term overlap     — query words directly appear in document signals
                            or extracted text sample.

    The higher of the two passes wins.
    """
    query_lower = query.lower()
    query_words = set(re.sub(r"[^\w\s]", "", query_lower).split())

    if not query_words:
        return 0.0

    signals = document.extracted_signals or {}

    # --- Pass 1: intent triggers ---
    intent_score = 0.0
    for section, triggers in _INTENT_TRIGGERS.items():
        for trigger in triggers:
            if trigger in query_lower:
                # Only boost if the document actually has content for this section
                if section in ("skills", "experience", "education", "certifications", "projects"):
                    if signals.get(section):
                        intent_score = max(intent_score, 0.6)
                    else:
                        # Document doesn't have that section but query is still profile-related
                        intent_score = max(intent_score, 0.3)
                else:
                    # Generic resume/summary intent
                    intent_score = max(intent_score, 0.5)
                break

    # --- Pass 2: direct term overlap ---
    signal_terms: set[str] = set()
    for key in ("skills", "document_keywords", "certifications"):
        for item in signals.get(key, []):
            signal_terms.update(item.lower().split())

    text_sample = (document.extracted_text or "")[:500].lower()
    text_words = set(re.sub(r"[^\w\s]", "", text_sample).split())

    all_doc_terms = signal_terms | text_words
    matched = len(query_words & all_doc_terms)
    overlap_score = matched / max(len(query_words), 1)

    return min(max(intent_score, overlap_score), 1.0)


def _build_document_context(query: str, user_documents: list, threshold: float = 0.15) -> str:
    """
    Returns a context string with only relevant document snippets.
    Returns an empty string if no document clears the relevance threshold.

    Args:
        query:          The latest user message.
        user_documents: List of UserDocument ORM objects.
        threshold:      Minimum relevance score (0–1) to include a document.
                        Lower = more liberal, higher = stricter.
                        0.15 is a sensible default for resume/career docs.
    """
    if not user_documents:
        return ""

    relevant_snippets: List[str] = []

    for doc in user_documents:
        score = _score_relevance(query, doc)

        if score < threshold:
            continue

        signals = doc.extracted_signals or {}
        text = (doc.extracted_text or "").strip()
        snippet_parts: List[str] = []

        # Compact, high-signal fields first
        if signals.get("skills"):
            snippet_parts.append(f"Skills: {', '.join(signals['skills'][:10])}")

        if signals.get("experience"):
            snippet_parts.append("Experience:\n" + "\n".join(signals["experience"][:4]))

        if signals.get("education"):
            snippet_parts.append("Education:\n" + "\n".join(signals["education"][:3]))

        if signals.get("certifications"):
            snippet_parts.append("Certifications:\n" + "\n".join(signals["certifications"][:3]))

        if signals.get("projects"):
            snippet_parts.append("Projects:\n" + "\n".join(signals["projects"][:3]))

        # Fall back to raw text excerpt only when signals are empty
        if not snippet_parts and text:
            snippet_parts.append(text[:800])

        if snippet_parts:
            header = f"[{doc.document_type.upper()}: {doc.filename}]"
            relevant_snippets.append(header + "\n" + "\n".join(snippet_parts))

    return "\n\n".join(relevant_snippets)


# =========================
# MAIN CHAT API
# =========================

async def generate_ai_response(
    messages: List[Dict[str, str]],
    model: str | None = None,
    temperature: float = 0.7,
    max_tokens: int = 700,
    user_documents: list | None = None,
) -> Tuple[str, int]:
    """
    Generate a full (non-streaming) AI response.

    If user_documents are provided, the last user message is scored against
    each document. Only relevant snippets are injected as a system message —
    irrelevant documents are silently ignored.
    """
    messages = list(messages)  # don't mutate the caller's list

    if user_documents:
        last_user_msg = next(
            (m["content"] for m in reversed(messages) if m.get("role") == "user"),
            "",
        )
        doc_context = _build_document_context(last_user_msg, user_documents)

        if doc_context:
            system_msg = {
                "role": "system",
                "content": (
                    "You have access to the following relevant information from "
                    "the user's personal documents. Use it naturally when answering "
                    "— don't quote it robotically or mention the document unless asked:\n\n"
                    + doc_context
                ),
            }
            # Insert system message at the front
            messages = [system_msg] + messages

    chunks: List[str] = []
    async for chunk in stream_groq_response(messages, model, temperature, max_tokens):
        chunks.append(chunk)

    text = "".join(chunks).strip()

    if not text:
        raise RuntimeError("Groq returned empty response")

    return text, max(1, len(text.split()))


async def stream_groq_response(
    messages: List[Dict[str, str]],
    model: str | None = None,
    temperature: float = 0.7,
    max_tokens: int = 700,
) -> AsyncIterator[str]:
    """
    Stream a response from Groq (OpenAI-compatible SSE).
    Falls back to mock response in development when GROQ_API_KEY is unset.
    """
    if not settings.GROQ_API_KEY:
        text, _ = _mock_response(messages)
        yield text
        return

    payload = {
        "model": model or settings.GROQ_MODEL,
        "messages": _sanitize_messages(messages),
        "temperature": temperature,
        "max_tokens": max_tokens,
        "stream": True,
    }

    headers = {
        "Authorization": f"Bearer {settings.GROQ_API_KEY}",
        "Content-Type": "application/json",
    }

    try:
        async with httpx.AsyncClient(timeout=60) as client:
            async with client.stream("POST", GROQ_URL, headers=headers, json=payload) as response:
                response.raise_for_status()

                async for line in response.aiter_lines():
                    if not line.startswith("data:"):
                        continue

                    data = line.removeprefix("data:").strip()

                    if data == "[DONE]":
                        break

                    try:
                        event = json.loads(data)
                    except json.JSONDecodeError:
                        logger.warning("groq_stream_json_error", data=data[:200])
                        continue

                    delta = event.get("choices", [{}])[0].get("delta", {})
                    content = delta.get("content")

                    if content:
                        yield content

    except Exception as exc:
        logger.error("groq_api_error", error=str(exc))

        if settings.ENVIRONMENT != "production":
            text, _ = _mock_response(messages)
            yield text
            return

        raise


# =========================
# EMBEDDINGS
# =========================

async def generate_embedding(text: str) -> List[float]:
    """
    Generate a text embedding via OpenAI.
    Falls back to a deterministic mock vector in development.
    """
    if not settings.OPENAI_API_KEY:
        return _mock_embedding(text, 1536)

    client = _get_openai_client()

    try:
        response = await client.embeddings.create(
            model=settings.OPENAI_EMBEDDING_MODEL,
            input=text,
        )
        return response.data[0].embedding

    except Exception as exc:
        logger.error("embedding_error", error=str(exc))

        if settings.ENVIRONMENT != "production":
            return _mock_embedding(text, 1536)

        raise


# =========================
# HEALTH CHECK
# =========================

async def check_groq_status() -> Dict[str, Any]:
    if not settings.GROQ_API_KEY:
        return {
            "provider": "groq",
            "configured": False,
            "connected": False,
        }

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            res = await client.get(
                "https://api.groq.com/openai/v1/models",
                headers={"Authorization": f"Bearer {settings.GROQ_API_KEY}"},
            )
            res.raise_for_status()

        return {
            "provider": "groq",
            "configured": True,
            "connected": True,
            "model": settings.GROQ_MODEL,
        }

    except Exception as e:
        return {
            "provider": "groq",
            "configured": True,
            "connected": False,
            "error": str(e),
        }


# =========================
# MOCK (DEV MODE)
# =========================

def _mock_response(messages: List[Dict[str, str]]) -> Tuple[str, int]:
    return (
        "Mock response: system is running without GROQ_API_KEY.",
        8,
    )


def _mock_embedding(text: str, dimension: int) -> List[float]:
    import numpy as np

    digest = hashlib.sha256(text.encode()).digest()
    seed = int.from_bytes(digest[:8], "big")
    rng = np.random.default_rng(seed)

    vec = rng.normal(size=dimension).astype("float32")
    vec /= (np.linalg.norm(vec) or 1)

    return vec.tolist()
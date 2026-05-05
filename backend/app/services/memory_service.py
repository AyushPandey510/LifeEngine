"""
Memory Service
Handles semantic memory using FAISS vector store
"""
import os
import json
import pickle
from datetime import datetime, timezone
import numpy as np
import faiss
from typing import Any, List, Optional
import structlog

from app.core.config import settings
from app.services.ai_service import generate_embedding

logger = structlog.get_logger()

# FAISS index storage directory
FAISS_DIR = settings.FAISS_DIR


def _get_user_index_path(user_id: str) -> str:
    """Get path to user's FAISS index file"""
    return os.path.join(FAISS_DIR, f"{user_id}_index.pkl")


def _get_user_index(user_id: str) -> Optional[faiss.IndexFlatIP]:
    """
    Load user's FAISS index from disk
    Returns None if no index exists yet
    """
    index_path = _get_user_index_path(user_id)
    
    if not os.path.exists(index_path):
        return None
    
    try:
        with open(index_path, "rb") as f:
            data = pickle.load(f)
            return data.get("index")
    except Exception as e:
        logger.error("failed_to_load_faiss_index", user_id=user_id, error=str(e))
        return None


def _save_user_index(user_id: str, index: faiss.IndexFlatIP, metadata: dict):
    """Save user's FAISS index to disk"""
    os.makedirs(FAISS_DIR, exist_ok=True)
    index_path = _get_user_index_path(user_id)
    
    try:
        with open(index_path, "wb") as f:
            pickle.dump({"index": index, "metadata": metadata}, f)
    except Exception as e:
        logger.error("failed_to_save_faiss_index", user_id=user_id, error=str(e))


def _load_metadata(user_id: str) -> dict:
    metadata_path = _get_user_index_path(user_id).replace("_index.pkl", "_meta.json")
    if os.path.exists(metadata_path):
        with open(metadata_path, "r") as f:
            return json.load(f)
    return {"count": 0, "messages": []}


def _save_metadata(user_id: str, metadata: dict) -> None:
    os.makedirs(FAISS_DIR, exist_ok=True)
    metadata_path = _get_user_index_path(user_id).replace("_index.pkl", "_meta.json")
    with open(metadata_path, "w") as f:
        json.dump(metadata, f)


async def store_memory_text(
    user_id: str,
    text: str,
    *,
    embedding_text: str | None = None,
    conversation_id: str | None = None,
    source: str = "chat",
    extra: dict[str, Any] | None = None,
) -> None:
    """Store one retrievable text item in the user's FAISS memory."""
    try:
        embedding = await generate_embedding(embedding_text or text)
        embedding_array = np.array([embedding]).astype("float32")
        faiss.normalize_L2(embedding_array)

        index = _get_user_index(user_id)
        if index is None:
            index = faiss.IndexFlatIP(len(embedding))
        elif index.d != len(embedding):
            logger.warning(
                "faiss_dimension_mismatch_skipping_memory",
                user_id=user_id,
                expected=index.d,
                actual=len(embedding),
            )
            return

        index.add(embedding_array)
        metadata = _load_metadata(user_id)
        metadata["count"] = int(metadata.get("count") or len(metadata.get("messages", []))) + 1
        metadata.setdefault("messages", []).append({
            "text": text[:2000],
            "index": metadata["count"] - 1,
            "conversation_id": conversation_id,
            "source": source,
            "extra": extra or {},
            "created_at": datetime.now(timezone.utc).isoformat(),
        })

        _save_user_index(user_id, index, metadata)
        _save_metadata(user_id, metadata)
        logger.info("memory_text_stored", user_id=user_id, source=source, total_items=metadata["count"])
    except Exception as e:
        logger.error("failed_to_store_memory_text", user_id=user_id, source=source, error=str(e))


async def store_interaction(
    user_id: str,
    user_message: str,
    ai_response: str,
    conversation_id: str | None = None,
):
    """
    Store user-AI interaction in FAISS vector store
    Called asynchronously after each chat message
    """
    try:
        combined_text = f"User: {user_message}\nAssistant: {ai_response}"
        await store_memory_text(
            user_id,
            combined_text,
            embedding_text=user_message,
            conversation_id=conversation_id,
            source="chat",
            extra={
                "user_text": user_message[:1000],
                "assistant_text": ai_response[:1000],
            },
        )
        
    except Exception as e:
        logger.error("failed_to_store_memory", user_id=user_id, error=str(e))


async def retrieve_memories(
    user_id: str,
    current_message: str,
    top_k: int = 3,
    min_score: float = 0.25,
    conversation_id: str | None = None,
    include_global: bool = True,
) -> List[str]:
    """
    Retrieve most relevant past conversations for current message
    
    Args:
        user_id: User's unique identifier
        current_message: The current message to find similar memories for
        top_k: Number of similar memories to retrieve
    
    Returns:
        List of most relevant past conversation texts
    """
    try:
        # Load user's index
        index = _get_user_index(user_id)
        if index is None or index.ntotal == 0:
            return []
        
        # Generate embedding for current message
        query_embedding = await generate_embedding(current_message)
        query_array = np.array([query_embedding]).astype("float32")
        faiss.normalize_L2(query_array)
        
        # Search for similar vectors
        search_k = min(max(top_k * 8, top_k), index.ntotal)
        distances, indices = index.search(query_array, search_k)
        
        # Load metadata to get actual text
        metadata = _load_metadata(user_id)
        
        # Extract relevant messages. Low-score matches are ignored to avoid
        # injecting unrelated personal context into the Future Self prompt.
        memories = []
        for score, idx in zip(distances[0], indices[0]):
            if idx >= 0 and idx < len(metadata.get("messages", [])):
                if float(score) >= min_score:
                    item = metadata["messages"][idx]
                    item_conversation_id = item.get("conversation_id")
                    is_global = item_conversation_id is None and item.get("source") in {"document", "profile", "chat"}
                    if conversation_id and item_conversation_id not in {None, conversation_id}:
                        continue
                    if item_conversation_id is None and not include_global and not is_global:
                        continue
                    text = item.get("text") or item.get("user_text") or ""
                    if text:
                        memories.append(text)
        
        # Apply recency boost
        # (can be enhanced with timestamps for more sophisticated boosting)
        
        return memories[:top_k]
        
    except Exception as e:
        logger.error("failed_to_retrieve_memories", user_id=user_id, error=str(e))
        return []


def chunk_text(text: str, chunk_size: int = 1200, overlap: int = 150) -> list[str]:
    """Split document text into overlapping chunks for retrieval."""
    normalized = " ".join(text.split())
    if not normalized:
        return []
    chunks = []
    start = 0
    while start < len(normalized):
        end = min(len(normalized), start + chunk_size)
        chunks.append(normalized[start:end])
        if end == len(normalized):
            break
        start = max(0, end - overlap)
    return chunks


async def store_document_chunks(
    user_id: str,
    document_id: str,
    filename: str,
    text: str,
    conversation_id: str | None = None,
) -> None:
    """Store parsed document chunks in retrieval memory."""
    for index, chunk in enumerate(chunk_text(text)):
        await store_memory_text(
            user_id,
            f"Document context from {filename}, chunk {index + 1}:\n{chunk}",
            embedding_text=chunk,
            conversation_id=conversation_id,
            source="document",
            extra={"document_id": document_id, "filename": filename, "chunk": index + 1},
        )


async def get_memory_count(user_id: str) -> int:
    """Get total number of stored memories for a user"""
    try:
        index = _get_user_index(user_id)
        if index is None:
            return 0
        return index.ntotal
    except Exception:
        return 0

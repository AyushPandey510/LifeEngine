"""
Memory Service
Handles semantic memory using FAISS vector store
"""
import os
import json
import pickle
import numpy as np
import faiss
from typing import List, Optional
import structlog

from app.services.ai_service import generate_embedding

logger = structlog.get_logger()

# FAISS index storage directory
FAISS_DIR = os.environ.get("FAISS_DIR", "/app/faiss_indexes")


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


async def store_interaction(user_id: str, user_message: str, ai_response: str):
    """
    Store user-AI interaction in FAISS vector store
    Called asynchronously after each chat message
    """
    try:
        # Combine user message and AI response for embedding
        combined_text = f"User: {user_message}\nAI: {ai_response}"
        
        # Generate embedding
        embedding = await generate_embedding(combined_text)
        
        # Convert to numpy array and normalize (for cosine similarity)
        embedding_array = np.array([embedding]).astype("float32")
        faiss.normalize_L2(embedding_array)
        
        # Get or create index
        index = _get_user_index(user_id)
        if index is None:
            # Create new index with Inner Product (cosine similarity)
            dimension = len(embedding)
            index = faiss.IndexFlatIP(dimension)
        
        # Add embedding to index
        index.add(embedding_array)
        
        # Load metadata or create new
        metadata_path = _get_user_index_path(user_id).replace("_index.pkl", "_meta.json")
        if os.path.exists(metadata_path):
            with open(metadata_path, "r") as f:
                metadata = json.load(f)
        else:
            metadata = {"count": 0, "messages": []}
        
        # Update metadata
        metadata["count"] += 1
        metadata["messages"].append({
            "text": combined_text[:500],  # Store truncated text
            "index": metadata["count"] - 1
        })
        
        # Save index and metadata
        _save_user_index(user_id, index, metadata)
        
        with open(metadata_path, "w") as f:
            json.dump(metadata, f)
        
        logger.info("interaction_stored_in_memory", user_id=user_id, total_items=metadata["count"])
        
    except Exception as e:
        logger.error("failed_to_store_memory", user_id=user_id, error=str(e))


async def retrieve_memories(user_id: str, current_message: str, top_k: int = 3) -> List[str]:
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
        distances, indices = index.search(query_array, min(top_k, index.ntotal))
        
        # Load metadata to get actual text
        metadata_path = _get_user_index_path(user_id).replace("_index.pkl", "_meta.json")
        if not os.path.exists(metadata_path):
            return []
        
        with open(metadata_path, "r") as f:
            metadata = json.load(f)
        
        # Extract relevant messages
        memories = []
        for idx in indices[0]:
            if idx >= 0 and idx < len(metadata.get("messages", [])):
                memories.append(metadata["messages"][idx]["text"])
        
        # Apply recency boost
        # (can be enhanced with timestamps for more sophisticated boosting)
        
        return memories[:top_k]
        
    except Exception as e:
        logger.error("failed_to_retrieve_memories", user_id=user_id, error=str(e))
        return []


async def get_memory_count(user_id: str) -> int:
    """Get total number of stored memories for a user"""
    try:
        index = _get_user_index(user_id)
        if index is None:
            return 0
        return index.ntotal
    except Exception:
        return 0
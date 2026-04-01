"""
AI Service
Handles LLM interactions with OpenAI/Anthropic/Google Gemini
"""
import os
from typing import List, Dict, Any, Tuple
import structlog

from app.core.config import settings

logger = structlog.get_logger()

# Global clients - initialized lazily
_openai_client = None
_gemini_client = None


def _get_openai_client():
    """Get or create OpenAI client"""
    global _openai_client
    if _openai_client is None:
        from openai import AsyncOpenAI
        _openai_client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
    return _openai_client


def _get_gemini_client():
    """Get or create Google Gemini client"""
    global _gemini_client
    if _gemini_client is None:
        import google.generativeai as genai
        genai.configure(api_key=settings.GEMINI_API_KEY)
        _gemini_client = genai
    return _gemini_client


async def generate_ai_response(
    messages: List[Dict[str, str]],
    model: str = None,
    max_tokens: int = 500,
    temperature: float = 0.7,
    provider: str = "auto"
) -> Tuple[str, int]:
    """
    Generate AI response using OpenAI, Anthropic, or Google Gemini API
    
    Args:
        messages: List of message dicts with 'role' and 'content'
        model: Model to use (defaults to settings.OPENAI_MODEL or settings.GEMINI_MODEL)
        max_tokens: Maximum tokens in response
        temperature: Creativity level (0-1)
        provider: 'auto', 'openai', 'anthropic', or 'gemini'
    
    Returns:
        Tuple of (response_text, tokens_used)
    """
    # Auto-select provider based on available API keys
    if provider == "auto":
        if settings.GEMINI_API_KEY:
            provider = "gemini"
        elif settings.OPENAI_API_KEY:
            provider = "openai"
        else:
            return _mock_response(messages), 50
    
    if provider == "gemini":
        return await _generate_gemini_response(messages, model, max_tokens, temperature)
    elif provider == "openai":
        return await _generate_openai_response(messages, model, max_tokens, temperature)
    else:
        return _mock_response(messages), 50


async def _generate_gemini_response(
    messages: List[Dict[str, str]],
    model: str = None,
    max_tokens: int = 500,
    temperature: float = 0.7
) -> Tuple[str, int]:
    """Generate response using Google Gemini API"""
    if not settings.GEMINI_API_KEY:
        return _mock_response(messages), 50
    
    client = _get_gemini_client()
    model = model or settings.GEMINI_MODEL
    
    try:
        # Convert messages to Gemini format
        gemini_messages = []
        for msg in messages:
            role = "model" if msg.get("role") == "assistant" else "user"
            gemini_messages.append({
                "role": role,
                "parts": [msg.get("content", "")]
            })
        
        # Use the GenerativeModel
        gen_model = client.GenerativeModel(model_name=model)
        
        response = await gen_model.generate_content_async(
            gemini_messages,
            generation_config={
                "max_output_tokens": max_tokens,
                "temperature": temperature,
            }
        )
        
        response_text = response.text
        # Gemini doesn't provide token counts in the same way
        tokens_used = len(response_text.split()) * 1.3  # Rough estimate
        
        logger.info(
            "gemini_response_generated",
            model=model,
            tokens=tokens_used
        )
        
        return response_text, int(tokens_used)
        
    except Exception as e:
        logger.error("gemini_api_error", error=str(e))
        raise


async def generate_embedding(text: str) -> List[float]:
    """
    Generate text embedding using OpenAI text-embedding model
    
    Args:
        text: Text to embed
    
    Returns:
        List of embedding values (1536 dimensions for text-embedding-3-small)
    """
    if not settings.OPENAI_API_KEY:
        # Return mock embedding for development
        import numpy as np
        return np.random.rand(1536).tolist()
    
    client = _get_openai_client()
    
    try:
        response = await client.embeddings.create(
            model="text-embedding-3-small",
            input=text
        )
        
        return response.data[0].embedding
        
    except Exception as e:
        logger.error("embedding_generation_failed", error=str(e))
        raise


def _mock_response(messages: List[Dict[str, str]]) -> str:
    """Mock AI response for development without API key"""
    # Get user's latest message
    user_message = None
    for msg in reversed(messages):
        if msg.get("role") == "user":
            user_message = msg.get("content", "")
            break
    
    # Simple responses based on message content
    message_lower = user_message.lower() if user_message else ""
    
    if "goal" in message_lower or "achieve" in message_lower:
        return "I remember when we set our first big goal. The key is to break it into smaller, daily actions. What specific step can you take today?"
    elif "decision" in message_lower or "should i" in message_lower:
        return "Looking at your patterns, I notice you've been most successful when you've given yourself time to think it through. Let me walk you through what typically happens with decisions like this..."
    elif "habit" in message_lower or "strug" in message_lower:
        return "Consistency beats intensity. The best way to build a habit is to start with just 2 minutes a day. What small version of this habit could you do today?"
    else:
        return "I remember this feeling well. The most important thing is to start, even if it's imperfect. What's one small step you can take right now?"
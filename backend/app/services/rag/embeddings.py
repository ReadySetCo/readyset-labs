# -*- coding: utf-8 -*-
"""
Embedding Service - Uses Gemini embeddings for semantic search.
"""

import os
import logging
from typing import List, Optional
import google.generativeai as genai

logger = logging.getLogger(__name__)


class EmbeddingService:
    """Generate embeddings using Gemini API."""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        self._configured = False
        self._failure_count = 0
        if self.api_key:
            genai.configure(api_key=self.api_key)
            self._configured = True
        else:
            logger.warning("[Embeddings] GEMINI_API_KEY not set — RAG search will not work")
        self.model = "models/text-embedding-004"
        self.dimension = 768  # Gemini embedding dimension

    def embed_text(self, text: str) -> List[float]:
        """Generate embedding for a single text."""
        if not self._configured:
            return [0.0] * self.dimension
        try:
            if not text or not text.strip():
                return [0.0] * self.dimension

            # Truncate long text
            text = text[:2000]

            result = genai.embed_content(
                model=self.model,
                content=text,
                task_type="retrieval_document"
            )
            self._failure_count = 0  # Reset on success
            return result['embedding']
        except Exception as e:
            self._failure_count += 1
            if self._failure_count <= 5:
                logger.error(f"[Embeddings] embed_text error ({self._failure_count}): {e}")
            elif self._failure_count == 6:
                logger.error(f"[Embeddings] Suppressing further embedding errors (API key or quota issue?)")
            elif self._failure_count % 50 == 0:
                logger.warning(f"[Embeddings] Still failing — {self._failure_count} total errors")
            return [0.0] * self.dimension

    def embed_query(self, query: str) -> List[float]:
        """Generate embedding for a search query."""
        if not self._configured:
            logger.warning("[Embeddings] Cannot embed query — GEMINI_API_KEY not set")
            return [0.0] * self.dimension
        try:
            if not query or not query.strip():
                return [0.0] * self.dimension

            result = genai.embed_content(
                model=self.model,
                content=query,
                task_type="retrieval_query"
            )
            return result['embedding']
        except Exception as e:
            logger.error(f"[Embeddings] embed_query error: {e}")
            return [0.0] * self.dimension
    
    def embed_batch(self, texts: List[str], batch_size: int = 100) -> List[List[float]]:
        """Generate embeddings for multiple texts."""
        embeddings = []
        
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i+batch_size]
            try:
                # Process batch
                for text in batch:
                    emb = self.embed_text(text)
                    embeddings.append(emb)
            except Exception as e:
                logger.error(f"Batch embedding error: {e}")
                # Fill with zeros for failed batch
                embeddings.extend([[0.0] * self.dimension] * len(batch))
        
        return embeddings


# Singleton
_service: Optional[EmbeddingService] = None

def get_embedding_service() -> EmbeddingService:
    global _service
    if _service is None:
        _service = EmbeddingService()
    return _service

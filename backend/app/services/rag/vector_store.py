# -*- coding: utf-8 -*-
"""
Vector Store - ChromaDB integration for semantic search.
"""

import os
import logging
from typing import List, Dict, Any, Optional
from pathlib import Path

logger = logging.getLogger(__name__)


class VectorStore:
    """ChromaDB-based vector store for RAG with automatic recovery."""
    
    def __init__(self, persist_dir: str = "vector_db"):
        self.persist_dir = Path(persist_dir)
        self.persist_dir.mkdir(parents=True, exist_ok=True)
        
        self.client = None
        self.collection = None
        self.embedder = None
        self._is_healthy = False
        
        # Initialize with auto-recovery
        self._initialize()
    
    def _initialize(self, retry_clean: bool = True):
        """Initialize ChromaDB with automatic corruption recovery."""
        try:
            import chromadb
            from chromadb.config import Settings
            
            self.client = chromadb.PersistentClient(
                path=str(self.persist_dir),
                settings=Settings(anonymized_telemetry=False)
            )
            
            # Get or create main collection
            self.collection = self.client.get_or_create_collection(
                name="research_data",
                metadata={"hnsw:space": "cosine"}
            )
            
            # Embedding service
            from .embeddings import get_embedding_service
            self.embedder = get_embedding_service()
            
            self._is_healthy = True
            logger.info(f"[VectorStore] Initialized successfully at {self.persist_dir}")
            
        except Exception as e:
            error_msg = str(e).lower()
            
            # Detect corruption errors
            if any(kw in error_msg for kw in ['compaction', 'hnsw', 'segment', 'corrupt', 'invalid']):
                if retry_clean:
                    logger.warning(f"[VectorStore] Database appears corrupted, attempting recovery...")
                    self._recover_from_corruption()
                else:
                    logger.error(f"[VectorStore] Failed to recover: {e}")
                    self._is_healthy = False
            else:
                logger.error(f"[VectorStore] Initialization error: {e}")
                self._is_healthy = False
    
    def _recover_from_corruption(self):
        """Attempt to recover from a corrupted database."""
        import shutil
        
        try:
            # Backup the corrupted DB
            if self.persist_dir.exists():
                backup_path = self.persist_dir.parent / f"{self.persist_dir.name}_corrupted_backup"
                if backup_path.exists():
                    shutil.rmtree(backup_path)
                shutil.move(str(self.persist_dir), str(backup_path))
                logger.info(f"[VectorStore] Moved corrupted DB to {backup_path}")
            
            # Create fresh directory
            self.persist_dir.mkdir(parents=True, exist_ok=True)
            
            # Try to reinitialize
            self._initialize(retry_clean=False)
            
            if self._is_healthy:
                logger.info(f"[VectorStore] Recovery successful - database recreated")
            else:
                logger.error(f"[VectorStore] Recovery failed")
                
        except Exception as e:
            logger.error(f"[VectorStore] Recovery error: {e}")
            self._is_healthy = False
    
    @property
    def is_available(self) -> bool:
        """Check if the vector store is healthy and available."""
        return self._is_healthy and self.collection is not None
    
    def index_session(
        self,
        session_id: int,
        documents: List[Dict[str, Any]],
        chunk_size: int = 500
    ) -> Dict[str, Any]:
        """
        Index all documents for a research session.
        
        Args:
            session_id: Research session ID
            documents: List of dicts with: content, source_type, source_url, sentiment, author
            chunk_size: Max characters per chunk
            
        Returns: Stats about indexing
        """
        logger.info(f"[VectorStore] Indexing {len(documents)} docs for session {session_id}")
        
        # First, delete any existing data for this session
        self.delete_session(session_id)
        
        chunks = []
        metadatas = []
        ids = []
        
        for doc_idx, doc in enumerate(documents):
            content = doc.get('content', '') or ''
            if not content.strip():
                continue
            
            # Chunk the content
            doc_chunks = self._chunk_text(content, chunk_size)
            
            for chunk_idx, chunk in enumerate(doc_chunks):
                chunk_id = f"s{session_id}_d{doc_idx}_c{chunk_idx}"
                
                chunks.append(chunk)
                ids.append(chunk_id)
                
                # ChromaDB only accepts primitive types (str, int, float, bool)
                # Convert all values to appropriate types, never None
                metadatas.append({
                    "session_id": int(session_id),
                    "source_type": str(doc.get('source_type') or 'unknown'),
                    "source_url": str(doc.get('source_url') or ''),
                    "sentiment": str(doc.get('sentiment') or ''),
                    "author": str(doc.get('author') or ''),
                    "doc_index": int(doc_idx),
                    "chunk_index": int(chunk_idx),
                })
        
        if not chunks:
            logger.warning(f"[VectorStore] No content to index for session {session_id}")
            return {"indexed": 0, "chunks": 0}
        
        # Generate embeddings
        logger.info(f"[VectorStore] Generating embeddings for {len(chunks)} chunks...")
        embeddings = self.embedder.embed_batch(chunks)
        
        # Add to collection in batches
        batch_size = 500
        for i in range(0, len(chunks), batch_size):
            end = min(i + batch_size, len(chunks))
            self.collection.add(
                ids=ids[i:end],
                embeddings=embeddings[i:end],
                documents=chunks[i:end],
                metadatas=metadatas[i:end]
            )
        
        logger.info(f"[VectorStore] Indexed {len(chunks)} chunks for session {session_id}")
        
        return {
            "indexed": len(documents),
            "chunks": len(chunks),
            "total_chunks": len(chunks),
            "session_id": session_id
        }
    
    def search(
        self,
        query: str,
        session_id: int,
        n_results: int = 20,
        source_filter: Optional[str] = None,
        sentiment_filter: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Search for relevant content using semantic similarity.
        
        Args:
            query: User's question
            session_id: Limit to this session
            n_results: Number of results to return
            source_filter: Optional source type filter (e.g., "reddit")
            sentiment_filter: Optional sentiment filter (e.g., "negative", "positive")
            
        Returns: List of matching chunks with metadata
        """
        # Check if store is healthy
        if not self.is_available:
            logger.warning(f"[VectorStore] Store not available, returning empty results")
            return []
        
        try:
            # Generate query embedding
            query_embedding = self.embedder.embed_query(query)
            
            # Build filter - ChromaDB requires $and for multiple conditions
            where_conditions = [{"session_id": session_id}]
            if source_filter:
                where_conditions.append({"source_type": source_filter})
            if sentiment_filter:
                where_conditions.append({"sentiment": sentiment_filter})
            
            # Use $and for multiple conditions, single dict for one condition
            if len(where_conditions) == 1:
                where_filter = where_conditions[0]
            else:
                where_filter = {"$and": where_conditions}
            
            # Search
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=n_results,
                where=where_filter,
                include=["documents", "metadatas", "distances"]
            )
            
            # Format results
            output = []
            if results and results.get('documents'):
                docs = results['documents'][0]
                metas = results['metadatas'][0]
                dists = results['distances'][0]
                
                for doc, meta, dist in zip(docs, metas, dists):
                    output.append({
                        "content": doc,
                        "source_type": meta.get('source_type', 'unknown'),
                        "source_url": meta.get('source_url', ''),
                        "sentiment": meta.get('sentiment', ''),
                        "author": meta.get('author', ''),
                        "similarity": 1 - dist,  # Convert distance to similarity
                    })
            
            logger.info(f"[VectorStore] Search found {len(output)} results")
            return output
            
        except Exception as e:
            logger.error(f"[VectorStore] Search error: {e}")
            return []
    
    def delete_session(self, session_id: int) -> int:
        """Delete all indexed data for a session."""
        try:
            # Get all IDs for this session
            results = self.collection.get(
                where={"session_id": session_id},
                include=[]
            )
            
            if results and results.get('ids'):
                ids_to_delete = results['ids']
                if ids_to_delete:
                    self.collection.delete(ids=ids_to_delete)
                    logger.info(f"[VectorStore] Deleted {len(ids_to_delete)} chunks for session {session_id}")
                    return len(ids_to_delete)
            
            return 0
        except Exception as e:
            logger.error(f"[VectorStore] Delete error: {e}")
            return 0
    
    def get_session_stats(self, session_id: int) -> Dict[str, Any]:
        """Get stats about indexed data for a session."""
        try:
            results = self.collection.get(
                where={"session_id": session_id},
                include=["metadatas"]
            )
            
            if not results or not results.get('ids'):
                return {"chunks": 0, "sources": []}
            
            sources = set()
            for meta in results.get('metadatas', []):
                sources.add(meta.get('source_type', 'unknown'))
            
            return {
                "chunks": len(results['ids']),
                "sources": list(sources)
            }
        except Exception as e:
            return {"chunks": 0, "sources": [], "error": str(e)}
    
    def _chunk_text(self, text: str, chunk_size: int) -> List[str]:
        """Split text into chunks, trying to break at sentence boundaries."""
        if len(text) <= chunk_size:
            return [text]
        
        chunks = []
        sentences = text.replace('\n', '. ').split('. ')
        current_chunk = ""
        
        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue
            
            if len(current_chunk) + len(sentence) + 2 <= chunk_size:
                current_chunk += sentence + ". "
            else:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                
                # Handle very long sentences
                if len(sentence) > chunk_size:
                    # Force split
                    for i in range(0, len(sentence), chunk_size):
                        chunks.append(sentence[i:i+chunk_size])
                    current_chunk = ""
                else:
                    current_chunk = sentence + ". "
        
        if current_chunk:
            chunks.append(current_chunk.strip())
        
        return chunks


# Singleton
_store: Optional[VectorStore] = None

def get_vector_store(persist_dir: str = "vector_db") -> VectorStore:
    global _store
    if _store is None:
        _store = VectorStore(persist_dir)
    return _store

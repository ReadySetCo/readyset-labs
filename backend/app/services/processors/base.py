# -*- coding: utf-8 -*-
"""Base processor class for Knowledge Synthesizer."""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
import json
import logging

logger = logging.getLogger(__name__)


class BaseProcessor(ABC):
    """Base class for all content processors."""
    
    # Source types this processor handles
    SOURCE_TYPES: List[str] = []
    
    def __init__(self, llm_client=None):
        """
        Initialize processor with LLM client.
        
        Args:
            llm_client: Gemini or OpenAI client for processing
        """
        self.llm_client = llm_client
    
    @abstractmethod
    def get_prompt(self, content: str, metadata: Dict[str, Any]) -> str:
        """
        Generate the prompt for this content type.
        
        Args:
            content: Raw content to process
            metadata: Additional context (source_type, author, etc)
            
        Returns:
            Formatted prompt string
        """
        pass
    
    @abstractmethod
    def parse_response(self, response: str) -> Dict[str, Any]:
        """
        Parse LLM response into structured format.
        
        Args:
            response: Raw LLM response
            
        Returns:
            Structured dict with extracted data
        """
        pass
    
    async def process(
        self,
        content: str,
        metadata: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Process content using LLM.
        
        Args:
            content: Raw content
            metadata: Additional context
            
        Returns:
            Processed structured data
        """
        if not content or len(content.strip()) < 10:
            return {"error": "Content too short", "processed": False}
        
        try:
            prompt = self.get_prompt(content, metadata)
            
            if self.llm_client:
                response = await self._call_llm(prompt)
                parsed = self.parse_response(response)
                parsed["processed"] = True
                parsed["raw_content"] = content[:500]  # Keep snippet of raw
                return parsed
            else:
                # Fallback without LLM - basic extraction
                return self._basic_extraction(content, metadata)
                
        except Exception as e:
            logger.error(f"Error processing content: {e}")
            return {
                "error": str(e),
                "processed": False,
                "raw_content": content[:500]
            }
    
    async def _call_llm(self, prompt: str) -> str:
        """Call LLM with prompt."""
        import asyncio
        
        if hasattr(self.llm_client, 'generate_content'):
            # Gemini - use sync method with asyncio.to_thread
            try:
                # Run sync call in thread pool with timeout
                response = await asyncio.wait_for(
                    asyncio.to_thread(self.llm_client.generate_content, prompt),
                    timeout=30.0  # 30 second timeout per call
                )
                return response.text
            except asyncio.TimeoutError:
                logger.warning("LLM call timed out after 30s")
                raise Exception("LLM timeout")
        elif hasattr(self.llm_client, 'chat'):
            # OpenAI-style
            response = await self.llm_client.chat.completions.create(
                model="gpt-4",
                messages=[{"role": "user", "content": prompt}]
            )
            return response.choices[0].message.content
        else:
            raise ValueError("Unknown LLM client type")
    
    def _basic_extraction(
        self,
        content: str,
        metadata: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Basic extraction without LLM."""
        return {
            "content_snippet": content[:500],
            "source_type": metadata.get("source_type"),
            "processed": False,
            "note": "Processed without LLM"
        }
    
    @classmethod
    def handles_source(cls, source_type: str) -> bool:
        """Check if this processor handles the given source type."""
        return source_type in cls.SOURCE_TYPES

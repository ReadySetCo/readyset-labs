# -*- coding: utf-8 -*-
"""
AnythingLLM Integration - Connect to AnythingLLM API for RAG chat.
"""

import os
import logging
import aiohttp
from typing import Dict, Any, Optional, List

logger = logging.getLogger(__name__)


class AnythingLLMClient:
    """Client for AnythingLLM API."""
    
    def __init__(
        self,
        base_url: str = None,
        api_key: Optional[str] = None
    ):
        # Support both localhost and Docker container URL
        self.base_url = (base_url or os.getenv("ANYTHINGLLM_URL", "http://localhost:3001")).rstrip('/')
        self.api_key = api_key or os.getenv("ANYTHINGLLM_API_KEY", "")
    
    def _headers(self) -> Dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers
    
    async def chat(
        self,
        workspace_slug: str,
        message: str,
        mode: str = "chat"  # "chat" or "query"
    ) -> Dict[str, Any]:
        """
        Send a chat message to a workspace.
        
        Args:
            workspace_slug: The workspace slug (e.g., "lauta")
            message: User message
            mode: "chat" for conversation, "query" for one-off queries
            
        Returns: Response with answer and sources
        """
        url = f"{self.base_url}/api/v1/workspace/{workspace_slug}/chat"
        
        payload = {
            "message": message,
            "mode": mode
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    url,
                    json=payload,
                    headers=self._headers(),
                    timeout=aiohttp.ClientTimeout(total=300)  # 5 min for Gemini 3
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        return {
                            "success": True,
                            "response": data.get("textResponse", ""),
                            "sources": data.get("sources", []),
                            "type": data.get("type", ""),
                        }
                    else:
                        error = await resp.text()
                        logger.error(f"AnythingLLM error {resp.status}: {error}")
                        return {
                            "success": False,
                            "error": f"API error: {resp.status}",
                            "details": error
                        }
        except aiohttp.ClientError as e:
            logger.error(f"AnythingLLM connection error: {e}")
            return {
                "success": False,
                "error": "Connection error - is AnythingLLM running?",
                "details": str(e)
            }
        except Exception as e:
            logger.error(f"AnythingLLM error: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def is_available(self) -> bool:
        """Check if AnythingLLM server is configured and reachable."""
        return bool(self.base_url) and bool(self.api_key)

    async def search(
        self,
        query: str,
        brand_name: str,
        limit: int = 15
    ) -> List[Dict[str, Any]]:
        """
        Search AnythingLLM workspace for relevant documents via chat query mode.

        Args:
            query: Search query
            brand_name: Brand name to derive workspace slug
            limit: Max results to return

        Returns: List of result dicts with content and source
        """
        from . import anythingllm as _mod
        workspace_slug = _mod.get_workspace_slug(brand_name)

        # Use query mode to get relevant documents without conversation
        result = await self.chat(
            workspace_slug=workspace_slug,
            message=query,
            mode="query"
        )

        if not result.get("success"):
            return []

        # Extract sources as search results
        results = []
        for source in result.get("sources", [])[:limit]:
            results.append({
                "content": source.get("text", source.get("content", "")),
                "source": source.get("title", source.get("document", "anythingllm")),
                "similarity": source.get("score", 0.5),
            })

        # If we got a response but no sources, return the response as a single result
        if not results and result.get("response"):
            results.append({
                "content": result["response"][:500],
                "source": "anythingllm",
                "similarity": 0.5,
            })

        return results

    async def list_workspaces(self) -> List[Dict[str, Any]]:
        """List all workspaces."""
        url = f"{self.base_url}/api/v1/workspaces"
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=self._headers()) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        return data.get("workspaces", [])
                    return []
        except Exception as e:
            logger.error(f"Error listing workspaces: {e}")
            return []
    
    async def create_workspace(self, name: str) -> Optional[Dict[str, Any]]:
        """Create a new workspace."""
        url = f"{self.base_url}/api/v1/workspace/new"
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    url,
                    json={"name": name},
                    headers=self._headers()
                ) as resp:
                    if resp.status == 200:
                        return await resp.json()
                    return None
        except Exception as e:
            logger.error(f"Error creating workspace: {e}")
            return None
    
    async def upload_document(
        self,
        file_path: str,
        workspace_slug: str
    ) -> Dict[str, Any]:
        """Upload a document to a workspace."""
        # First upload to documents
        upload_url = f"{self.base_url}/api/v1/document/upload"
        
        try:
            async with aiohttp.ClientSession() as session:
                # Upload file
                with open(file_path, 'rb') as f:
                    data = aiohttp.FormData()
                    data.add_field('file', f, filename=os.path.basename(file_path))
                    
                    headers = {}
                    if self.api_key:
                        headers["Authorization"] = f"Bearer {self.api_key}"
                    
                    async with session.post(upload_url, data=data, headers=headers) as resp:
                        if resp.status != 200:
                            return {"success": False, "error": await resp.text()}
                        upload_result = await resp.json()
                
                # Add to workspace
                doc_location = upload_result.get("documents", [{}])[0].get("location", "")
                if doc_location:
                    add_url = f"{self.base_url}/api/v1/workspace/{workspace_slug}/update-embeddings"
                    async with session.post(
                        add_url,
                        json={"adds": [doc_location]},
                        headers=self._headers()
                    ) as resp:
                        if resp.status == 200:
                            return {"success": True, "document": doc_location}
                
                return {"success": False, "error": "Upload failed"}
                
        except Exception as e:
            logger.error(f"Error uploading document: {e}")
            return {"success": False, "error": str(e)}


# Singleton
_client: Optional[AnythingLLMClient] = None

def get_anythingllm_client() -> AnythingLLMClient:
    global _client
    if _client is None:
        # Ensure env vars are loaded
        from dotenv import load_dotenv
        load_dotenv()
        
        api_key = os.getenv("ANYTHINGLLM_API_KEY", "")
        logger.info(f"[AnythingLLM] Initializing client, API key present: {bool(api_key)}")
        _client = AnythingLLMClient(api_key=api_key)
    return _client


def get_workspace_slug(brand_name: str) -> str:
    """Convert brand name to a valid workspace slug."""
    import re
    # Convert to lowercase, replace spaces with hyphens, remove special chars
    slug = brand_name.lower().strip()
    slug = re.sub(r'[^a-z0-9\s-]', '', slug)
    slug = re.sub(r'[\s]+', '-', slug)
    slug = re.sub(r'-+', '-', slug)
    return slug[:50]  # Max 50 chars


async def sync_brand_to_workspace(
    brand_name: str,
    knowledge_base_dir: str = "knowledge_base"
) -> Dict[str, Any]:
    """
    Sync a brand's knowledge base files to AnythingLLM workspace.
    
    1. Ensure workspace exists (create if needed)
    2. Upload all .md files from the brand's knowledge_base folder
    
    Args:
        brand_name: Name of the brand
        knowledge_base_dir: Base directory for knowledge base exports
        
    Returns: Dict with sync stats
    """
    from pathlib import Path
    
    client = get_anythingllm_client()
    workspace_slug = get_workspace_slug(brand_name)
    
    logger.info(f"[AnythingLLM] Syncing brand '{brand_name}' to workspace '{workspace_slug}'")
    
    result = {
        "brand_name": brand_name,
        "workspace_slug": workspace_slug,
        "documents_uploaded": 0,
        "errors": [],
        "success": False
    }
    
    try:
        # 1. Check if workspace exists, create if not
        workspaces = await client.list_workspaces()
        workspace_exists = any(w.get("slug") == workspace_slug for w in workspaces)
        
        if not workspace_exists:
            logger.info(f"[AnythingLLM] Creating workspace: {workspace_slug}")
            create_result = await client.create_workspace(brand_name)
            if not create_result:
                result["errors"].append("Failed to create workspace")
                return result
            # Get the actual slug from creation result
            workspace_slug = create_result.get("workspace", {}).get("slug", workspace_slug)
            result["workspace_slug"] = workspace_slug
            logger.info(f"[AnythingLLM] Workspace created: {workspace_slug}")
        
        # 2. Find brand's knowledge base folder
        kb_path = Path(knowledge_base_dir)
        brand_folder = None
        
        # Try exact match first
        for folder in kb_path.iterdir():
            if folder.is_dir():
                # Match by sanitized name or exact name
                folder_slug = get_workspace_slug(folder.name)
                if folder_slug == workspace_slug or folder.name.lower() == brand_name.lower():
                    brand_folder = folder
                    break
        
        if not brand_folder:
            result["errors"].append(f"Knowledge base folder not found for '{brand_name}'")
            return result
        
        # 3. Upload all .md files
        md_files = list(brand_folder.glob("*.md"))
        logger.info(f"[AnythingLLM] Found {len(md_files)} markdown files to upload")
        
        for md_file in md_files:
            try:
                upload_result = await client.upload_document(
                    file_path=str(md_file),
                    workspace_slug=workspace_slug
                )
                if upload_result.get("success"):
                    result["documents_uploaded"] += 1
                    logger.info(f"[AnythingLLM] Uploaded: {md_file.name}")
                else:
                    result["errors"].append(f"Failed to upload {md_file.name}: {upload_result.get('error')}")
            except Exception as e:
                result["errors"].append(f"Error uploading {md_file.name}: {str(e)}")
        
        result["success"] = result["documents_uploaded"] > 0
        logger.info(f"[AnythingLLM] Sync complete: {result['documents_uploaded']} docs uploaded")
        
    except Exception as e:
        logger.error(f"[AnythingLLM] Sync error: {e}")
        result["errors"].append(str(e))
    
    return result


async def get_brand_workspace_slug(session_id: int, db) -> Optional[str]:
    """
    Get the workspace slug for a session's brand.
    
    Args:
        session_id: Research session ID
        db: Database session
        
    Returns: Workspace slug or None
    """
    from sqlalchemy import select
    from ..models import ResearchSession, Brand
    
    try:
        result = await db.execute(
            select(Brand).join(ResearchSession).where(ResearchSession.id == session_id)
        )
        brand = result.scalar_one_or_none()
        if brand:
            return get_workspace_slug(brand.name)
    except Exception as e:
        logger.error(f"[AnythingLLM] Error getting brand for session {session_id}: {e}")
    
    return None

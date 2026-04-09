# -*- coding: utf-8 -*-
"""
Chat router - AI Chatbot endpoints for interacting with research data.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List
from pydantic import BaseModel

from ..database import get_db
from ..services.chatbot import ChatbotService


router = APIRouter()

# Store chatbot instances per session (simple in-memory)
_chatbot_sessions: dict = {}


class ChatMessage(BaseModel):
    """Chat message request."""
    message: str
    session_id: Optional[int] = None
    brand_id: Optional[int] = None


class ChatResponse(BaseModel):
    """Chat response."""
    response: str
    sources: List[dict] = []
    timestamp: str
    error: Optional[str] = None


class GenerateScriptRequest(BaseModel):
    """Script generation request."""
    session_id: int
    prompt: str = ""
    style: str = "ugc"  # ugc, testimonial, educational, etc.


class VerbatimSearchRequest(BaseModel):
    """Verbatim search request."""
    session_id: int
    topic: str = ""
    sentiment: str = "any"  # positive, negative, neutral, any
    limit: int = 10


@router.post("/chat", response_model=ChatResponse)
async def chat(
    request: ChatMessage,
    db: AsyncSession = Depends(get_db)
):
    """
    Chat with the AI assistant about research data.
    
    The AI can:
    - Answer questions about scraped data
    - Find customer quotes and verbatims
    - Analyze trends and patterns
    - Generate ad scripts on demand
    
    Provide session_id or brand_id for context-aware responses.
    """
    print(f"[Router] Chat request: session_id={request.session_id}, message='{request.message[:50]}...'")
    
    try:
        # Get or create chatbot for this conversation
        session_key = f"s{request.session_id or 0}_b{request.brand_id or 0}"
        
        if session_key not in _chatbot_sessions:
            _chatbot_sessions[session_key] = ChatbotService(db)
        
        chatbot = _chatbot_sessions[session_key]
        # Update DB reference (in case connection changed)
        chatbot.db = db
        chatbot.api.db = db  # Also update the API's db reference
        
        # Process message
        result = await chatbot.chat(
            message=request.message,
            session_id=request.session_id,
            brand_id=request.brand_id
        )
        
        return ChatResponse(
            response=result.get("response", "No response"),
            sources=result.get("sources", []),
            timestamp=result.get("timestamp", ""),
            error=result.get("error")
        )
    except Exception as e:
        import traceback
        print(f"[Router] Error in chat: {type(e).__name__}: {e}")
        traceback.print_exc()
        return ChatResponse(
            response=f"Server error: {type(e).__name__}. Please try again.",
            sources=[],
            timestamp="",
            error=str(e)
        )


@router.post("/chat/generate-script")
async def generate_script(
    request: GenerateScriptRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Generate an ad script based on research data.
    
    Styles:
    - ugc: User-generated content style
    - testimonial: Customer testimonial format
    - educational: How-to / educational content
    - problem_solution: PAS framework
    """
    chatbot = ChatbotService(db)
    
    result = await chatbot.generate_script(
        session_id=request.session_id,
        prompt=request.prompt,
        style=request.style
    )
    
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    
    return result


@router.post("/chat/find-verbatims")
async def find_verbatims(
    request: VerbatimSearchRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Find verbatim customer quotes on a specific topic.
    
    Returns real quotes from scraped data that can be used in ads.
    """
    chatbot = ChatbotService(db)
    
    verbatims = await chatbot.find_verbatims(
        session_id=request.session_id,
        topic=request.topic,
        sentiment=request.sentiment,
        limit=request.limit
    )
    
    return {
        "verbatims": verbatims,
        "count": len(verbatims),
        "topic": request.topic,
        "sentiment": request.sentiment
    }


@router.post("/chat/clear")
async def clear_chat_history(
    session_id: Optional[int] = None,
    brand_id: Optional[int] = None
):
    """Clear conversation history for a session."""
    session_key = f"s{session_id or 0}_b{brand_id or 0}"
    
    if session_key in _chatbot_sessions:
        _chatbot_sessions[session_key].clear_history()
        return {"success": True, "message": "Chat history cleared"}
    
    return {"success": True, "message": "No history to clear"}


@router.get("/chat/suggestions")
async def get_chat_suggestions(
    session_id: Optional[int] = None,
    db: AsyncSession = Depends(get_db)
):
    """
    Get suggested questions for the chatbot based on available data.
    """
    suggestions = [
        "What are the top pain points mentioned by customers?",
        "Find me positive reviews about the product",
        "What objections do customers have?",
        "Generate a UGC-style ad script",
        "What are competitors saying?",
        "Show me verbatim quotes I can use in ads",
        "What topics are trending in customer discussions?",
        "Compare sentiment across different platforms"
    ]
    
    if session_id:
        suggestions.insert(0, "Summarize the key findings from this research")
        suggestions.insert(1, "What are the best hooks based on the data?")
    
    return {"suggestions": suggestions}


# ============== AnythingLLM Integration ==============

class AnythingLLMChatRequest(BaseModel):
    """Request for AnythingLLM chat."""
    message: str
    workspace: Optional[str] = None  # Workspace slug (optional if session_id provided)
    session_id: Optional[int] = None  # Session ID to get brand workspace


@router.post("/chat/rag")
async def chat_with_anythingllm(
    request: AnythingLLMChatRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Chat using AnythingLLM's RAG capabilities.
    
    This connects to your AnythingLLM instance and uses
    the documents you've uploaded to that workspace.
    
    You can provide either:
    - workspace: Direct workspace slug
    - session_id: Will auto-detect the brand's workspace
    
    First, set ANYTHINGLLM_API_KEY in your .env file.
    Get it from AnythingLLM: Settings > Developer API
    """
    from ..services.anythingllm import get_anythingllm_client, get_brand_workspace_slug, get_workspace_slug
    from ..models import ResearchSession, Brand
    from sqlalchemy import select
    
    # Determine workspace slug
    workspace_slug = request.workspace
    brand_name = None
    
    if request.session_id and not workspace_slug:
        # Get brand from session
        try:
            result = await db.execute(
                select(Brand).join(ResearchSession).where(ResearchSession.id == request.session_id)
            )
            brand = result.scalar_one_or_none()
            if brand:
                brand_name = brand.name
                workspace_slug = get_workspace_slug(brand.name)
                print(f"[Chat/RAG] Session {request.session_id} -> Brand: {brand_name} -> Workspace: {workspace_slug}")
        except Exception as e:
            print(f"[Chat/RAG] Error getting brand for session {request.session_id}: {e}")
    
    if not workspace_slug:
        return {
            "response": "No workspace specified. Please provide either a workspace slug or session_id.",
            "sources": [],
            "success": False,
            "error": "missing_workspace"
        }
    
    client = get_anythingllm_client()
    result = await client.chat(
        workspace_slug=workspace_slug,
        message=request.message
    )
    
    if result.get("success"):
        return {
            "response": result.get("response", ""),
            "sources": result.get("sources", []),
            "success": True,
            "workspace": workspace_slug,
            "brand_name": brand_name
        }
    else:
        return {
            "response": result.get("error", "Unknown error"),
            "sources": [],
            "success": False,
            "error": result.get("details", ""),
            "workspace": workspace_slug
        }


@router.get("/chat/rag/workspaces")
async def list_anythingllm_workspaces():
    """List available AnythingLLM workspaces."""
    from ..services.anythingllm import get_anythingllm_client
    
    client = get_anythingllm_client()
    workspaces = await client.list_workspaces()
    
    return {"workspaces": workspaces}

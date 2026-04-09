# -*- coding: utf-8 -*-
"""
Idea Bank Router - Save and manage creative ideas.

Endpoints:
- POST /ideas/ - Save a new idea
- GET /ideas/ - List all saved ideas
- GET /ideas/{id} - Get a specific idea
- PUT /ideas/{id} - Update an idea
- DELETE /ideas/{id} - Delete an idea
- POST /ideas/{id}/favorite - Toggle favorite status
- GET /ideas/by-brand/{brand_id} - Get ideas for a brand
- GET /ideas/by-type/{idea_type} - Get ideas by type
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, update, or_
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime, timezone

from ..database import get_db
from ..models import SavedIdea, Brand

router = APIRouter(prefix="/ideas", tags=["idea-bank"])


# Pydantic models

class IdeaCreate(BaseModel):
    brand_id: Optional[int] = None
    session_id: Optional[int] = None
    idea_type: str  # hook, script, thumbnail, angle, quote
    title: Optional[str] = None
    content: str
    hook_type: Optional[str] = None
    target_emotion: Optional[str] = None
    target_persona: Optional[str] = None
    platform_fit: Optional[List[str]] = None
    strength_score: Optional[int] = None
    source: Optional[str] = None
    source_detail: Optional[str] = None
    tags: Optional[List[str]] = None
    notes: Optional[str] = None


class IdeaUpdate(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None
    hook_type: Optional[str] = None
    target_emotion: Optional[str] = None
    target_persona: Optional[str] = None
    platform_fit: Optional[List[str]] = None
    strength_score: Optional[int] = None
    tags: Optional[List[str]] = None
    notes: Optional[str] = None
    is_favorite: Optional[bool] = None


class IdeaResponse(BaseModel):
    id: int
    brand_id: Optional[int]
    session_id: Optional[int]
    idea_type: str
    title: Optional[str]
    content: str
    hook_type: Optional[str]
    target_emotion: Optional[str]
    target_persona: Optional[str]
    platform_fit: Optional[List[str]]
    strength_score: Optional[int]
    source: Optional[str]
    source_detail: Optional[str]
    tags: Optional[List[str]]
    notes: Optional[str]
    is_favorite: bool
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


# Endpoints

@router.post("/", response_model=IdeaResponse)
async def create_idea(idea: IdeaCreate, db: AsyncSession = Depends(get_db)):
    """Save a new idea to the Idea Bank."""
    new_idea = SavedIdea(
        brand_id=idea.brand_id,
        session_id=idea.session_id,
        idea_type=idea.idea_type,
        title=idea.title,
        content=idea.content,
        hook_type=idea.hook_type,
        target_emotion=idea.target_emotion,
        target_persona=idea.target_persona,
        platform_fit=idea.platform_fit,
        strength_score=idea.strength_score,
        source=idea.source,
        source_detail=idea.source_detail,
        tags=idea.tags,
        notes=idea.notes
    )
    
    db.add(new_idea)
    await db.commit()
    await db.refresh(new_idea)
    
    return new_idea


@router.get("/", response_model=List[IdeaResponse])
async def list_ideas(
    idea_type: Optional[str] = None,
    brand_id: Optional[int] = None,
    is_favorite: Optional[bool] = None,
    tag: Optional[str] = None,
    search: Optional[str] = None,
    limit: int = Query(default=50, le=200),
    offset: int = 0,
    db: AsyncSession = Depends(get_db)
):
    """List saved ideas with optional filters."""
    query = select(SavedIdea).order_by(SavedIdea.created_at.desc())
    
    if idea_type:
        query = query.where(SavedIdea.idea_type == idea_type)
    if brand_id:
        query = query.where(SavedIdea.brand_id == brand_id)
    if is_favorite is not None:
        query = query.where(SavedIdea.is_favorite == is_favorite)
    if search:
        # Escape SQL wildcard characters to prevent wildcard injection
        safe_search = search.replace("%", "\\%").replace("_", "\\_")
        search_filter = or_(
            SavedIdea.content.ilike(f"%{safe_search}%"),
            SavedIdea.title.ilike(f"%{safe_search}%"),
            SavedIdea.notes.ilike(f"%{safe_search}%")
        )
        query = query.where(search_filter)
    
    query = query.offset(offset).limit(limit)
    
    result = await db.execute(query)
    ideas = result.scalars().all()
    
    # Filter by tag if specified (tags is JSON array)
    if tag:
        ideas = [i for i in ideas if i.tags and tag in i.tags]
    
    return ideas


@router.get("/{idea_id}", response_model=IdeaResponse)
async def get_idea(idea_id: int, db: AsyncSession = Depends(get_db)):
    """Get a specific idea by ID."""
    result = await db.execute(select(SavedIdea).where(SavedIdea.id == idea_id))
    idea = result.scalar_one_or_none()
    
    if not idea:
        raise HTTPException(status_code=404, detail="Idea not found")
    
    return idea


@router.put("/{idea_id}", response_model=IdeaResponse)
async def update_idea(idea_id: int, idea_update: IdeaUpdate, db: AsyncSession = Depends(get_db)):
    """Update an existing idea."""
    result = await db.execute(select(SavedIdea).where(SavedIdea.id == idea_id))
    idea = result.scalar_one_or_none()
    
    if not idea:
        raise HTTPException(status_code=404, detail="Idea not found")
    
    # Update only provided fields
    update_data = idea_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(idea, key, value)
    
    idea.updated_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(idea)
    
    return idea


@router.delete("/{idea_id}")
async def delete_idea(idea_id: int, db: AsyncSession = Depends(get_db)):
    """Delete an idea."""
    result = await db.execute(select(SavedIdea).where(SavedIdea.id == idea_id))
    idea = result.scalar_one_or_none()
    
    if not idea:
        raise HTTPException(status_code=404, detail="Idea not found")
    
    await db.delete(idea)
    await db.commit()
    
    return {"success": True, "message": f"Idea {idea_id} deleted"}


@router.post("/{idea_id}/favorite", response_model=IdeaResponse)
async def toggle_favorite(idea_id: int, db: AsyncSession = Depends(get_db)):
    """Toggle favorite status of an idea."""
    result = await db.execute(select(SavedIdea).where(SavedIdea.id == idea_id))
    idea = result.scalar_one_or_none()
    
    if not idea:
        raise HTTPException(status_code=404, detail="Idea not found")
    
    idea.is_favorite = not idea.is_favorite
    idea.updated_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(idea)
    
    return idea


@router.get("/by-brand/{brand_id}", response_model=List[IdeaResponse])
async def get_ideas_by_brand(
    brand_id: int,
    idea_type: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """Get all ideas for a specific brand."""
    query = select(SavedIdea).where(SavedIdea.brand_id == brand_id).order_by(SavedIdea.created_at.desc())
    
    if idea_type:
        query = query.where(SavedIdea.idea_type == idea_type)
    
    result = await db.execute(query)
    return result.scalars().all()


@router.get("/by-type/{idea_type}", response_model=List[IdeaResponse])
async def get_ideas_by_type(
    idea_type: str,
    limit: int = Query(default=50, le=200),
    db: AsyncSession = Depends(get_db)
):
    """Get all ideas of a specific type."""
    query = (
        select(SavedIdea)
        .where(SavedIdea.idea_type == idea_type)
        .order_by(SavedIdea.created_at.desc())
        .limit(limit)
    )
    
    result = await db.execute(query)
    return result.scalars().all()


@router.get("/stats/summary")
async def get_idea_stats(db: AsyncSession = Depends(get_db)):
    """Get summary statistics for the Idea Bank."""
    # Total count
    total_result = await db.execute(select(SavedIdea))
    all_ideas = total_result.scalars().all()
    
    # Count by type
    by_type = {}
    by_brand = {}
    favorites_count = 0
    
    for idea in all_ideas:
        # By type
        by_type[idea.idea_type] = by_type.get(idea.idea_type, 0) + 1
        
        # By brand
        if idea.brand_id:
            by_brand[idea.brand_id] = by_brand.get(idea.brand_id, 0) + 1
        
        # Favorites
        if idea.is_favorite:
            favorites_count += 1
    
    return {
        "total_ideas": len(all_ideas),
        "favorites": favorites_count,
        "by_type": by_type,
        "by_brand": by_brand
    }

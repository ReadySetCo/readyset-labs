"""
Brands router - CRUD operations for brands.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List

from ..database import get_db
from ..models import Brand
from ..schemas import BrandCreate, BrandResponse, APIResponse

router = APIRouter()


@router.post("/", response_model=BrandResponse, status_code=status.HTTP_201_CREATED)
async def create_brand(
    brand_data: BrandCreate,
    db: AsyncSession = Depends(get_db)
):
    """Create a new brand to research."""
    brand = Brand(
        name=brand_data.name,
        website_url=brand_data.website_url,
        ad_library_url=brand_data.ad_library_url,
    )
    db.add(brand)
    await db.commit()
    await db.refresh(brand)
    return brand


@router.get("/", response_model=List[BrandResponse])
async def list_brands(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db)
):
    """List all brands."""
    result = await db.execute(
        select(Brand).offset(skip).limit(limit).order_by(Brand.created_at.desc())
    )
    brands = result.scalars().all()
    return brands


@router.get("/{brand_id}", response_model=BrandResponse)
async def get_brand(
    brand_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Get a specific brand by ID."""
    result = await db.execute(select(Brand).where(Brand.id == brand_id))
    brand = result.scalar_one_or_none()
    
    if not brand:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Brand with id {brand_id} not found"
        )
    
    return brand


@router.delete("/{brand_id}", response_model=APIResponse)
async def delete_brand(
    brand_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Delete a brand."""
    result = await db.execute(select(Brand).where(Brand.id == brand_id))
    brand = result.scalar_one_or_none()
    
    if not brand:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Brand with id {brand_id} not found"
        )
    
    await db.delete(brand)
    await db.commit()
    
    return APIResponse(
        success=True,
        message=f"Brand '{brand.name}' deleted successfully"
    )





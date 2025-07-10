"""Leads API router."""

from fastapi import APIRouter, HTTPException, Query
from typing import Dict, Any, List, Optional
from datetime import datetime

from ...database.operations import LeadOperations
from ...utils import get_logger

logger = get_logger(__name__)
router = APIRouter()

@router.get("/")
async def get_leads(
    status: Optional[str] = Query(None, description="Filter by status"),
    source: Optional[str] = Query(None, description="Filter by source"),
    has_email: Optional[bool] = Query(None, description="Filter by email presence"),
    has_website: Optional[bool] = Query(None, description="Filter by website presence"),
    limit: Optional[int] = Query(50, description="Maximum results to return"),
    offset: int = Query(0, description="Number of results to skip")
) -> Dict[str, Any]:
    """Get leads with optional filtering."""
    try:
        lead_ops = LeadOperations()
        leads = lead_ops.search_leads(
            status=status,
            source=source,
            has_email=has_email,
            has_website=has_website,
            limit=limit,
            offset=offset
        )
        
        # Convert to dict for JSON serialization
        leads_data = []
        for lead in leads:
            leads_data.append({
                "id": lead.id,
                "name": lead.name,
                "website": lead.website,
                "email": lead.email,
                "category": lead.category,
                "location": lead.location,
                "phone": lead.phone,
                "rating": lead.rating,
                "review_count": lead.review_count,
                "status": lead.status,
                "source": lead.source,
                "scraped_at": lead.scraped_at.isoformat() if lead.scraped_at else None,
                "created_at": lead.created_at.isoformat() if lead.created_at else None
            })
        
        return {
            "success": True,
            "data": leads_data,
            "count": len(leads_data),
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to get leads: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{lead_id}")
async def get_lead(lead_id: int) -> Dict[str, Any]:
    """Get a specific lead by ID."""
    try:
        lead_ops = LeadOperations()
        lead = lead_ops.get_lead(lead_id)
        
        if not lead:
            raise HTTPException(status_code=404, detail="Lead not found")
        
        return {
            "success": True,
            "data": {
                "id": lead.id,
                "name": lead.name,
                "website": lead.website,
                "email": lead.email,
                "category": lead.category,
                "location": lead.location,
                "phone": lead.phone,
                "rating": lead.rating,
                "review_count": lead.review_count,
                "status": lead.status,
                "source": lead.source,
                "scraped_at": lead.scraped_at.isoformat() if lead.scraped_at else None,
                "created_at": lead.created_at.isoformat() if lead.created_at else None
            },
            "timestamp": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get lead {lead_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/{lead_id}")
async def update_lead(lead_id: int, updates: Dict[str, Any]) -> Dict[str, Any]:
    """Update a lead."""
    try:
        lead_ops = LeadOperations()
        success = lead_ops.update_lead(lead_id, updates)
        
        if not success:
            raise HTTPException(status_code=404, detail="Lead not found")
        
        return {
            "success": True,
            "message": "Lead updated successfully",
            "timestamp": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update lead {lead_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/{lead_id}")
async def delete_lead(lead_id: int) -> Dict[str, Any]:
    """Delete a lead."""
    try:
        lead_ops = LeadOperations()
        success = lead_ops.delete_lead(lead_id)
        
        if not success:
            raise HTTPException(status_code=404, detail="Lead not found")
        
        return {
            "success": True,
            "message": "Lead deleted successfully",
            "timestamp": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete lead {lead_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/stats/summary")
async def get_lead_stats() -> Dict[str, Any]:
    """Get lead statistics."""
    try:
        lead_ops = LeadOperations()
        stats = lead_ops.get_lead_statistics()
        
        return {
            "success": True,
            "data": stats,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to get lead stats: {e}")
        raise HTTPException(status_code=500, detail=str(e)) 
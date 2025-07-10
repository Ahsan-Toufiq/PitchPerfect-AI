"""Dashboard API router."""

from fastapi import APIRouter, HTTPException
from typing import Dict, Any
from datetime import datetime, timedelta

from ...database.operations import get_dashboard_data
from ...utils import get_logger

logger = get_logger(__name__)
router = APIRouter()

@router.get("/stats")
async def get_dashboard_stats() -> Dict[str, Any]:
    """Get dashboard statistics."""
    try:
        data = get_dashboard_data()
        return {
            "success": True,
            "data": data,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Failed to get dashboard stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/activity")
async def get_recent_activity() -> Dict[str, Any]:
    """Get recent system activity."""
    try:
        from ...database.operations import LeadOperations, EmailOperations, AnalysisOperations
        
        # Get recent leads
        lead_ops = LeadOperations()
        recent_leads = lead_ops.search_leads(limit=10)
        
        # Get recent emails
        email_ops = EmailOperations()
        recent_emails = email_ops.get_recent_emails(limit=10)
        
        # Get recent analyses
        analysis_ops = AnalysisOperations()
        recent_analyses = analysis_ops.get_recent_analyses(limit=10)
        
        activities = []
        
        # Add lead activities
        for lead in recent_leads:
            activities.append({
                "type": "lead",
                "title": f"New lead scraped: {lead.name}",
                "description": f"Lead from {lead.source} in {lead.location}",
                "timestamp": lead.scraped_at.isoformat() if lead.scraped_at else None,
                "data": {
                    "id": lead.id,
                    "name": lead.name,
                    "website": lead.website,
                    "email": lead.email,
                    "category": lead.category,
                    "location": lead.location
                }
            })
        
        # Add email activities
        for email in recent_emails:
            activities.append({
                "type": "email",
                "title": f"Email sent to {email.lead_name}",
                "description": f"Email status: {email.status}",
                "timestamp": email.sent_at.isoformat() if email.sent_at else None,
                "data": {
                    "id": email.id,
                    "lead_id": email.lead_id,
                    "status": email.status,
                    "bounce_reason": email.bounce_reason
                }
            })
        
        # Add analysis activities
        for analysis in recent_analyses:
            activities.append({
                "type": "analysis",
                "title": f"Website analyzed: {analysis.lead_name}",
                "description": f"Lighthouse score: {analysis.lighthouse_score}",
                "timestamp": analysis.analyzed_at.isoformat() if analysis.analyzed_at else None,
                "data": {
                    "id": analysis.id,
                    "lead_id": analysis.lead_id,
                    "lighthouse_score": analysis.lighthouse_score,
                    "seo_score": analysis.seo_score,
                    "performance_score": analysis.performance_score
                }
            })
        
        # Sort by timestamp (most recent first)
        activities.sort(key=lambda x: x["timestamp"] or "", reverse=True)
        
        return {
            "success": True,
            "data": activities[:20],  # Return last 20 activities
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to get recent activity: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/system-status")
async def get_system_status() -> Dict[str, Any]:
    """Get system status and health."""
    try:
        from ...config import get_settings
        from ...utils.rate_limiter import get_rate_limit_status
        
        settings = get_settings()
        
        # Check email configuration
        email_configured = settings.is_email_configured()
        
        # Check Ollama configuration
        ollama_configured = settings.is_ollama_configured()
        
        # Get rate limiting status
        rate_status = get_rate_limit_status()
        
        # Check database connection
        try:
            get_dashboard_data()
            database_status = "healthy"
        except Exception:
            database_status = "error"
        
        return {
            "success": True,
            "data": {
                "email_configured": email_configured,
                "ollama_configured": ollama_configured,
                "database_status": database_status,
                "rate_limiting": rate_status,
                "timestamp": datetime.now().isoformat()
            }
        }
        
    except Exception as e:
        logger.error(f"Failed to get system status: {e}")
        raise HTTPException(status_code=500, detail=str(e)) 
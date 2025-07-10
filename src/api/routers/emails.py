"""Emails API router."""

from fastapi import APIRouter, HTTPException, BackgroundTasks, Query
from pydantic import BaseModel
from typing import Dict, Any, List, Optional
from datetime import datetime

from ...email_system.orchestrator import EmailOrchestrator
from ...database.operations import EmailOperations
from ...utils import get_logger

logger = get_logger(__name__)
router = APIRouter()

class EmailRequest(BaseModel):
    lead_id: Optional[int] = None
    template: Optional[str] = None
    dry_run: bool = True
    max_emails: int = 50

# Store active email jobs
active_jobs: Dict[str, Dict[str, Any]] = {}

@router.post("/send")
async def send_emails(
    request: EmailRequest,
    background_tasks: BackgroundTasks
) -> Dict[str, Any]:
    """Send email campaign."""
    try:
        # Generate job ID
        job_id = f"email_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{hash(str(request.lead_id)) % 10000}"
        
        # Initialize job status
        active_jobs[job_id] = {
            "status": "starting",
            "progress": 0,
            "total_emails": 0,
            "sent_emails": 0,
            "error": None,
            "started_at": datetime.now().isoformat(),
            "request": request.dict()
        }
        
        # Start email sending in background
        background_tasks.add_task(
            run_email_job,
            job_id,
            request.lead_id,
            request.template,
            request.dry_run,
            request.max_emails
        )
        
        return {
            "success": True,
            "data": {
                "job_id": job_id,
                "status": "starting",
                "message": "Email campaign started"
            },
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to start email campaign: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/status/{job_id}")
async def get_email_status(job_id: str) -> Dict[str, Any]:
    """Get email job status."""
    try:
        if job_id not in active_jobs:
            raise HTTPException(status_code=404, detail="Job not found")
        
        job = active_jobs[job_id]
        
        return {
            "success": True,
            "data": {
                "job_id": job_id,
                "status": job["status"],
                "progress": job["progress"],
                "total_emails": job["total_emails"],
                "sent_emails": job["sent_emails"],
                "error": job["error"],
                "started_at": job["started_at"],
                "request": job["request"]
            },
            "timestamp": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get email status: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/jobs")
async def get_active_email_jobs() -> Dict[str, Any]:
    """Get all active email jobs."""
    try:
        jobs_data = []
        for job_id, job in active_jobs.items():
            jobs_data.append({
                "job_id": job_id,
                "status": job["status"],
                "progress": job["progress"],
                "total_emails": job["total_emails"],
                "sent_emails": job["sent_emails"],
                "started_at": job["started_at"],
                "request": job["request"]
            })
        
        return {
            "success": True,
            "data": jobs_data,
            "count": len(jobs_data),
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to get active email jobs: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/campaigns")
async def get_email_campaigns(
    status: Optional[str] = Query(None, description="Filter by status"),
    limit: Optional[int] = Query(50, description="Maximum results to return"),
    offset: int = Query(0, description="Number of results to skip")
) -> Dict[str, Any]:
    """Get email campaigns."""
    try:
        email_ops = EmailOperations()
        campaigns = email_ops.get_recent_emails(limit=limit, offset=offset)
        
        campaigns_data = []
        for campaign in campaigns:
            campaigns_data.append({
                "id": campaign.id,
                "lead_id": campaign.lead_id,
                "lead_name": campaign.lead_name,
                "email_content": campaign.email_content,
                "status": campaign.status,
                "sent_at": campaign.sent_at.isoformat() if campaign.sent_at else None,
                "bounce_reason": campaign.bounce_reason
            })
        
        return {
            "success": True,
            "data": campaigns_data,
            "count": len(campaigns_data),
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to get email campaigns: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/campaigns/{campaign_id}")
async def get_email_campaign(campaign_id: int) -> Dict[str, Any]:
    """Get specific email campaign."""
    try:
        email_ops = EmailOperations()
        campaign = email_ops.get_email_campaign(campaign_id)
        
        if not campaign:
            raise HTTPException(status_code=404, detail="Campaign not found")
        
        return {
            "success": True,
            "data": {
                "id": campaign.id,
                "lead_id": campaign.lead_id,
                "lead_name": campaign.lead_name,
                "email_content": campaign.email_content,
                "status": campaign.status,
                "sent_at": campaign.sent_at.isoformat() if campaign.sent_at else None,
                "bounce_reason": campaign.bounce_reason
            },
            "timestamp": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get email campaign: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/stats")
async def get_email_stats() -> Dict[str, Any]:
    """Get email statistics."""
    try:
        email_ops = EmailOperations()
        stats = email_ops.get_email_statistics()
        
        return {
            "success": True,
            "data": stats,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to get email stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/templates")
async def get_email_templates() -> Dict[str, Any]:
    """Get available email templates."""
    try:
        from ...email_system.template_engine import EmailTemplateEngine
        
        template_engine = EmailTemplateEngine()
        templates = template_engine.get_available_templates()
        
        return {
            "success": True,
            "data": templates,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to get email templates: {e}")
        raise HTTPException(status_code=500, detail=str(e))

async def run_email_job(
    job_id: str,
    lead_id: Optional[int],
    template: Optional[str],
    dry_run: bool,
    max_emails: int
):
    """Run email job in background."""
    try:
        # Update job status
        active_jobs[job_id]["status"] = "running"
        
        # Initialize email orchestrator
        email_orchestrator = EmailOrchestrator()
        
        if lead_id:
            # Send email to specific lead
            active_jobs[job_id]["total_emails"] = 1
            active_jobs[job_id]["progress"] = 50
            
            success = email_orchestrator.send_email_to_lead(
                lead_id, template=template, dry_run=dry_run
            )
            
            if success:
                active_jobs[job_id]["status"] = "completed"
                active_jobs[job_id]["sent_emails"] = 1
                active_jobs[job_id]["progress"] = 100
            else:
                active_jobs[job_id]["status"] = "failed"
                active_jobs[job_id]["error"] = "Failed to send email"
        else:
            # Send campaign emails
            from ...database.operations import LeadOperations
            lead_ops = LeadOperations()
            ready_leads = lead_ops.get_leads_for_email()
            
            # Limit to max_emails
            ready_leads = ready_leads[:max_emails]
            active_jobs[job_id]["total_emails"] = len(ready_leads)
            
            if not ready_leads:
                active_jobs[job_id]["status"] = "completed"
                active_jobs[job_id]["progress"] = 100
                return
            
            # Send emails
            sent_count = 0
            for lead in ready_leads:
                if active_jobs[job_id]["status"] == "cancelled":
                    break
                
                try:
                    success = email_orchestrator.send_email_to_lead(
                        lead.id, template=template, dry_run=dry_run
                    )
                    if success:
                        sent_count += 1
                    
                    active_jobs[job_id]["sent_emails"] = sent_count
                    active_jobs[job_id]["progress"] = int((sent_count / len(ready_leads)) * 100)
                except Exception as e:
                    logger.error(f"Failed to send email to lead {lead.id}: {e}")
            
            active_jobs[job_id]["status"] = "completed"
            active_jobs[job_id]["progress"] = 100
        
        logger.info(f"Email job {job_id} completed")
        
    except Exception as e:
        logger.error(f"Email job {job_id} failed: {e}")
        active_jobs[job_id]["status"] = "failed"
        active_jobs[job_id]["error"] = str(e) 
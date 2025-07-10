"""Scraping API router."""

from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends
from pydantic import BaseModel
from typing import Dict, Any, List, Optional
from datetime import datetime
from sqlalchemy.orm import Session
import uuid

from ...scraper.orchestrator import ScrapingOrchestrator
from ...database.operations import LeadOperations
from ...database.models import ScrapingJob, Lead
from ...utils import get_logger
from ...database import get_db

logger = get_logger(__name__)
router = APIRouter()

class ScrapingRequest(BaseModel):
    search_term: str
    source: str = "google"  # yelp, google, both
    max_leads: int = 50
    category: Optional[str] = None
    location: Optional[str] = None
    business_type: Optional[str] = None

class ScrapingResponse(BaseModel):
    job_id: str
    status: str
    message: str
    timestamp: str

# Store active scraping jobs
active_jobs: Dict[str, Dict[str, Any]] = {}

@router.post("/start")
async def start_scraping(
    request: ScrapingRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """Start a new scraping job."""
    try:
        # Create job record
        job = ScrapingJob(
            job_id=str(uuid.uuid4()),
            search_term=request.search_term,
            source=request.source,
            status="running",
            progress=0,
            total_listings=0,
            successful_extractions=0,
            business_type=request.business_type,
            location=request.location
        )
        db.add(job)
        db.commit()
        db.refresh(job)
        
        # Store job in memory for real-time updates
        active_jobs[job.job_id] = {
            "id": job.id,
            "job_id": job.job_id,
            "search_term": request.search_term,
            "status": "running",
            "progress": 0,
            "total_listings": 0,
            "successful_extractions": 0,
            "message": f"Starting scraping for: {request.search_term}",
            "start_time": datetime.utcnow(),
            "leads": []
        }
        
        # Start background scraping task
        background_tasks.add_task(
            run_scraping_job,
            job.job_id,
            request.search_term,
            request.source,
            request.max_leads,
            request.business_type,
            request.location,
            db
        )
        
        return {
            "data": {
                "id": job.id,
                "job_id": job.job_id,
                "status": "running",
                "message": f"Started scraping for: {request.search_term}",
                "search_term": request.search_term,
                "source": request.source
            }
        }
        
    except Exception as e:
        logger.error(f"Error starting scraping job: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/status/{job_id}")
async def get_scraping_status(job_id: str) -> Dict[str, Any]:
    """Get scraping job status."""
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
                "total_leads": job["total_leads"],
                "scraped_leads": job["scraped_leads"],
                "error": job["error"],
                "started_at": job["started_at"],
                "request": job["request"]
            },
            "timestamp": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get scraping status: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/jobs")
async def get_all_jobs() -> Dict[str, Any]:
    """Get all scraping jobs from database."""
    try:
        db = next(get_db())
        jobs = db.query(ScrapingJob).order_by(ScrapingJob.created_at.desc()).all()
        
        jobs_data = []
        for job in jobs:
            jobs_data.append({
                "id": job.id,
                "job_id": f"job_{job.id}",  # Generate a job_id for compatibility
                "search_term": job.search_term,
                "status": job.status,
                "progress": job.progress,
                "total_listings": job.total_listings,
                "successful_extractions": job.successful_extractions,
                "created_at": job.created_at.isoformat() if job.created_at else None,
                "completed_at": job.completed_at.isoformat() if job.completed_at else None,
                "error_message": job.error_message
            })
        
        return {
            "success": True,
            "data": jobs_data,
            "count": len(jobs_data),
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to get jobs: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/jobs/{job_id}/leads")
async def get_job_leads(job_id: int) -> Dict[str, Any]:
    """Get leads for a specific job."""
    try:
        db = next(get_db())
        
        # Get job to verify it exists
        job = db.query(ScrapingJob).filter(ScrapingJob.id == job_id).first()
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        
        # Get leads for this job (all leads in the system for now)
        # In a more sophisticated system, you'd link leads to specific jobs
        leads = db.query(Lead).order_by(Lead.scraped_at.desc()).all()
        
        leads_data = []
        for lead in leads:
            leads_data.append({
                "id": lead.id,
                "name": lead.name,
                "phone": lead.phone,
                "website": lead.website,
                "email": lead.email,
                "location": lead.location,
                "business_type": lead.business_type,
                "scraped_at": lead.scraped_at.isoformat() if lead.scraped_at else None,
                "status": lead.status
            })
        
        return {
            "success": True,
            "data": leads_data,
            "count": len(leads_data),
            "timestamp": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get job leads: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/jobs/{job_id}")
async def cancel_job(job_id: str) -> Dict[str, Any]:
    """Cancel a scraping job."""
    try:
        if job_id not in active_jobs:
            raise HTTPException(status_code=404, detail="Job not found")
        
        # Mark job as cancelled
        active_jobs[job_id]["status"] = "cancelled"
        
        # Update database job if it exists
        db = next(get_db())
        db_job = db.query(ScrapingJob).filter(ScrapingJob.id == active_jobs[job_id]["db_id"]).first()
        if db_job:
            db_job.status = "cancelled"
            db.commit()
        
        return {
            "success": True,
            "message": "Job cancelled successfully",
            "timestamp": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to cancel job: {e}")
        raise HTTPException(status_code=500, detail=str(e))

async def run_scraping_job(
    job_id: str,
    search_term: str,
    source: str,
    max_leads: int,
    business_type: Optional[str],
    location: Optional[str],
    db: Session
):
    """Run scraping job in background."""
    try:
        # Update job status
        active_jobs[job_id]["status"] = "running"
        
        # Update database job
        db_job = db.query(ScrapingJob).filter(ScrapingJob.job_id == job_id).first()
        if db_job:
            db_job.status = "running"
            db.commit()
        
        # Initialize scraper
        scraper = ScrapingOrchestrator()
        
        # Determine sources
        if source == "both":
            sources = ["yelp", "google"]
        else:
            sources = [source]
        
        total_leads = 0
        
        for src in sources:
            if active_jobs[job_id]["status"] == "cancelled":
                break
                
            # Update progress
            active_jobs[job_id]["progress"] = 50 if src == "google" else 0
            
            try:
                # Try to scrape leads from the requested source
                leads = scraper.scrape_leads(search_term, src, max_leads // len(sources))
                total_leads += len(leads)
            except Exception as e:
                logger.warning(f"Failed to scrape from {src}: {e}")
                leads = []
            
            # Update job status
            active_jobs[job_id]["scraped_leads"] = total_leads
            active_jobs[job_id]["progress"] = 100 if src == "google" else 50
            
            # Update database job
            if db_job:
                db_job.successful_extractions = total_leads
                db_job.progress = active_jobs[job_id]["progress"]
                db.commit()
        
        # Mark job as completed
        active_jobs[job_id]["status"] = "completed"
        active_jobs[job_id]["total_leads"] = total_leads
        active_jobs[job_id]["progress"] = 100
        
        # Update database job
        if db_job:
            db_job.status = "completed"
            db_job.successful_extractions = total_leads
            db_job.progress = 100
            db_job.completed_at = datetime.now()
            db.commit()
        
        logger.info(f"Scraping job {job_id} completed with {total_leads} leads")
        
    except Exception as e:
        logger.error(f"Scraping job {job_id} failed: {e}")
        active_jobs[job_id]["status"] = "failed"
        active_jobs[job_id]["error"] = str(e)
        
        # Update database job
        if db_job:
            db_job.status = "failed"
            db_job.error_message = str(e)
            db.commit() 
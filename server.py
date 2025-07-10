#!/usr/bin/env python3
"""
FastAPI server for PitchPerfect AI
"""

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import asyncio
import json
from datetime import datetime
import uuid

from src.database.models import get_db, Lead, ScrapingJob, EmailCampaign, WebsiteAnalysis
from src.scraper.gmaps_scraper import GoogleMapsScraper
from src.utils.logger import get_logger

# Initialize FastAPI app
app = FastAPI(
    title="PitchPerfect AI API",
    description="Lead generation and outreach system",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000", "http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static files are served by the separate frontend server
# app.mount("/", StaticFiles(directory="frontend/dist", html=True), name="static")

# Pydantic models for API
class ScrapingRequest(BaseModel):
    search_term: Optional[str] = None
    business_type: Optional[str] = None
    location: Optional[str] = None

class ScrapingResponse(BaseModel):
    job_id: str
    status: str
    message: str

class ScrapingStatus(BaseModel):
    job_id: str
    status: str
    progress: int
    total_listings: int
    successful_extractions: int
    message: str

class LeadData(BaseModel):
    id: int
    name: str
    phone: Optional[str]
    website: Optional[str]
    email: Optional[str]
    location: Optional[str]
    business_type: Optional[str]
    scraped_at: datetime
    status: str

# Global storage for active jobs (in production, use Redis)
active_jobs: Dict[str, Dict[str, Any]] = {}

logger = get_logger(__name__)

@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    return {"data": {"status": "healthy", "timestamp": datetime.utcnow()}}

@app.post("/api/scraping/start", response_model=None)
async def start_scraping(request: ScrapingRequest, background_tasks: BackgroundTasks):
    """Start a new scraping job."""
    try:
        # Create job ID
        job_id = str(uuid.uuid4())
        
        # Determine search term
        if request.search_term:
            search_term = request.search_term
        elif request.business_type and request.location:
            search_term = f"{request.business_type} in {request.location}"
        else:
            raise HTTPException(status_code=400, detail="Either search_term or both business_type and location must be provided")
        
        # Create job record in database
        db = next(get_db())
        job = ScrapingJob(
            job_id=job_id,  # Use the UUID as job_id
            search_term=search_term,
            status="pending",
            progress=0,
            total_listings=0,
            successful_extractions=0
        )
        db.add(job)
        db.commit()
        db.refresh(job)
        
        # Store job info in memory
        active_jobs[job_id] = {
            "db_id": job.id,
            "status": "running",
            "progress": 0,
            "total_listings": 0,
            "successful_extractions": 0,
            "message": "Starting scraping job...",
            "start_time": datetime.utcnow(),
            "loading_start_time": None,
            "scraping_start_time": None,
            "search_term": search_term
        }
        
        # Start scraping in background
        background_tasks.add_task(run_scraping_job, job_id, search_term)
        
        return {"data": {
            "job_id": job_id,
            "id": job.id,  # Database ID
            "status": "started",
            "message": f"Scraping job started for: {search_term}"
        }}
        
    except Exception as e:
        logger.error(f"Error starting scraping job: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/scraping/status/{job_id}", response_model=None)
async def get_scraping_status(job_id: str):
    """Get the status of a scraping job."""
    # First check active jobs
    if job_id in active_jobs:
        job_info = active_jobs[job_id]
        
        return {"data": ScrapingStatus(
            job_id=job_id,
            status=job_info["status"],
            progress=job_info["progress"],
            total_listings=job_info["total_listings"],
            successful_extractions=job_info["successful_extractions"],
            message=job_info["message"]
        ).dict()}
    
    # If not in active jobs, check database
    try:
        db = next(get_db())
        job = db.query(ScrapingJob).filter(ScrapingJob.id == int(job_id)).first()
        
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        
        return {"data": ScrapingStatus(
            job_id=job_id,
            status=job.status,
            progress=job.progress,
            total_listings=job.total_listings,
            successful_extractions=job.successful_extractions,
            message=f"Job {job.status}: {job.successful_extractions} leads extracted"
        ).dict()}
        
    except ValueError:
        raise HTTPException(status_code=404, detail="Job not found")
    except Exception as e:
        logger.error(f"Error getting job status: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/api/scraping/results/{job_id}")
async def get_scraping_results(job_id: str):
    """Get the results of a scraping job (works for both running and completed jobs)."""
    # First check active jobs
    if job_id in active_jobs:
        job_info = active_jobs[job_id]
        
        # Get leads from database (works for both running and completed jobs)
        db = next(get_db())
        leads = db.query(Lead).filter(Lead.scraped_at >= job_info.get("start_time")).all()
        
        return {"data": {
            "job_id": job_id,
            "job_status": job_info["status"],
            "leads": [
                {
                    "id": lead.id,
                    "name": lead.name,
                    "phone": lead.phone,
                    "website": lead.website,
                    "email": lead.email,
                    "location": lead.location,
                    "business_type": lead.business_type,
                    "scraped_at": lead.scraped_at,
                    "status": lead.status
                }
                for lead in leads
            ]
        }}
    
    # If not in active jobs, check database
    try:
        db = next(get_db())
        job = db.query(ScrapingJob).filter(ScrapingJob.id == int(job_id)).first()
        
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        
        # Get leads for this job (approximate by time range)
        leads = db.query(Lead).filter(
            Lead.scraped_at >= job.created_at,
            Lead.scraped_at <= (job.completed_at or datetime.utcnow())
        ).all()
        
        return {"data": {
            "job_id": job_id,
            "job_status": job.status,
            "leads": [
                {
                    "id": lead.id,
                    "name": lead.name,
                    "phone": lead.phone,
                    "website": lead.website,
                    "email": lead.email,
                    "location": lead.location,
                    "business_type": lead.business_type,
                    "scraped_at": lead.scraped_at,
                    "status": lead.status
                }
                for lead in leads
            ]
        }}
        
    except ValueError:
        raise HTTPException(status_code=404, detail="Job not found")
    except Exception as e:
        logger.error(f"Error getting job results: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/api/scraping/jobs")
async def get_scraping_jobs():
    """Get all scraping jobs from database."""
    db = next(get_db())
    jobs = db.query(ScrapingJob).order_by(ScrapingJob.created_at.desc()).all()
    
    return {"data": [
        {
            "id": job.id,
            "job_id": job.job_id,  # Use actual job_id field
            "search_term": job.search_term,
            "status": job.status,
            "progress": job.progress,
            "total_listings": job.total_listings,
            "successful_extractions": job.successful_extractions,
            "created_at": job.created_at,
            "completed_at": job.completed_at,
            "error_message": job.error_message
        }
        for job in jobs
    ]}

@app.get("/api/scraping/jobs/{job_id}/leads")
async def get_job_leads(job_id: int):
    """Get leads for a specific job from database."""
    db = next(get_db())
    job = db.query(ScrapingJob).filter(ScrapingJob.id == job_id).first()
    
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    # Get leads for this job (approximate by time range)
    leads = db.query(Lead).filter(
        Lead.scraped_at >= job.created_at,
        Lead.scraped_at <= (job.completed_at or datetime.utcnow())
    ).all()
    
    return {"data": {
        "job_id": job_id,
        "job": {
            "id": job.id,
            "search_term": job.search_term,
            "status": job.status,
            "progress": job.progress,
            "total_listings": job.total_listings,
            "successful_extractions": job.successful_extractions,
            "created_at": job.created_at,
            "completed_at": job.completed_at
        },
        "leads": [
            {
                "id": lead.id,
                "name": lead.name,
                "phone": lead.phone,
                "website": lead.website,
                "email": lead.email,
                "location": lead.location,
                "business_type": lead.business_type,
                "scraped_at": lead.scraped_at,
                "status": lead.status
            }
            for lead in leads
        ]
    }}

@app.delete("/api/scraping/jobs/{job_id}")
async def cancel_scraping_job(job_id: str):
    """Cancel a scraping job."""
    try:
        # Check if job exists in active jobs
        if job_id not in active_jobs:
            # Check if job exists in database
            db = next(get_db())
            job = db.query(ScrapingJob).filter(ScrapingJob.id == job_id).first()
            if not job:
                raise HTTPException(status_code=404, detail="Job not found")
            
            # Mark job as cancelled in database
            job.status = "cancelled"
            job.completed_at = datetime.utcnow()
            db.commit()
            
            return {"data": {"message": "Job cancelled successfully"}}
        
        # Mark job as cancelled in memory
        active_jobs[job_id]["status"] = "cancelled"
        active_jobs[job_id]["message"] = "Job cancelled by user"
        
        # Update database
        db = next(get_db())
        job = db.query(ScrapingJob).filter(ScrapingJob.id == active_jobs[job_id]["db_id"]).first()
        if job:
            job.status = "cancelled"
            job.completed_at = datetime.utcnow()
            db.commit()
        
        return {"data": {"message": "Job cancelled successfully"}}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error cancelling job {job_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/dashboard/stats")
async def get_dashboard_stats():
    """Get dashboard statistics."""
    db = next(get_db())
    
    # Get counts
    total_leads = db.query(Lead).count()
    total_jobs = db.query(ScrapingJob).count()
    completed_jobs = db.query(ScrapingJob).filter(ScrapingJob.status == "completed").count()
    total_campaigns = db.query(EmailCampaign).count()
    
    # Get recent activity
    recent_leads = db.query(Lead).order_by(Lead.scraped_at.desc()).limit(10).all()
    recent_jobs = db.query(ScrapingJob).order_by(ScrapingJob.created_at.desc()).limit(5).all()
    
    return {"data": {
        "stats": {
            "total_leads": total_leads,
            "total_jobs": total_jobs,
            "completed_jobs": completed_jobs,
            "total_campaigns": total_campaigns
        },
        "recent_leads": [
            {
                "id": lead.id,
                "name": lead.name,
                "phone": lead.phone,
                "website": lead.website,
                "scraped_at": lead.scraped_at
            }
            for lead in recent_leads
        ],
        "recent_jobs": [
            {
                "id": job.id,
                "search_term": job.search_term,
                "status": job.status,
                "progress": job.progress,
                "created_at": job.created_at
            }
            for job in recent_jobs
        ]
    }}

@app.get("/api/dashboard/activity")
async def get_dashboard_activity():
    """Get recent dashboard activity."""
    db = next(get_db())
    
    # Get recent leads and jobs
    recent_leads = db.query(Lead).order_by(Lead.scraped_at.desc()).limit(10).all()
    recent_jobs = db.query(ScrapingJob).order_by(ScrapingJob.created_at.desc()).limit(5).all()
    
    return {"data": {
        "recent_leads": [
            {
                "id": lead.id,
                "name": lead.name,
                "phone": lead.phone,
                "website": lead.website,
                "scraped_at": lead.scraped_at
            }
            for lead in recent_leads
        ],
        "recent_jobs": [
            {
                "id": job.id,
                "search_term": job.search_term,
                "status": job.status,
                "progress": job.progress,
                "created_at": job.created_at
            }
            for job in recent_jobs
        ]
    }}

@app.get("/api/dashboard/leads")
async def get_leads(page: int = 1, limit: int = 50, status: Optional[str] = None):
    """Get leads with pagination and filtering."""
    db = next(get_db())
    
    query = db.query(Lead)
    
    if status:
        query = query.filter(Lead.status == status)
    
    total = query.count()
    leads = query.order_by(Lead.scraped_at.desc()).offset((page - 1) * limit).limit(limit).all()
    
    return {"data": {
        "leads": [
            {
                "id": lead.id,
                "name": lead.name,
                "phone": lead.phone,
                "website": lead.website,
                "email": lead.email,
                "location": lead.location,
                "business_type": lead.business_type,
                "scraped_at": lead.scraped_at,
                "status": lead.status
            }
            for lead in leads
        ],
        "pagination": {
            "page": page,
            "limit": limit,
            "total": total,
            "pages": (total + limit - 1) // limit
        }
    }}

async def run_scraping_job(job_id: str, search_term: str):
    """Run the scraping job in background."""
    try:
        logger.info(f"Starting scraping job {job_id} for: {search_term}")
        
        # Update job status
        active_jobs[job_id]["status"] = "running"
        active_jobs[job_id]["start_time"] = datetime.utcnow()
        active_jobs[job_id]["message"] = "Initializing scraper..."
        
        # Initialize scraper
        scraper = GoogleMapsScraper()
        
        # Update database
        db = next(get_db())
        job = db.query(ScrapingJob).filter(ScrapingJob.id == active_jobs[job_id]["db_id"]).first()
        job.status = "running"
        db.commit()
        
        # Check for cancellation before starting
        if job_id in active_jobs and active_jobs[job_id]["status"] == "cancelled":
            logger.info(f"Scraping job {job_id} was cancelled before starting")
            return
        
        # Run scraping with progress updates and real-time saving
        results = await scraper.scrape_with_progress(
            search_term=search_term,
            progress_callback=lambda progress, total, successful, message, new_lead=None: update_progress_with_lead(job_id, progress, total, successful, message, new_lead, db)
        )
        
        # Check for cancellation before finalizing
        if job_id in active_jobs and active_jobs[job_id]["status"] == "cancelled":
            logger.info(f"Scraping job {job_id} was cancelled during execution")
            return
        
        # Update final status
        active_jobs[job_id]["status"] = "completed"
        active_jobs[job_id]["message"] = f"Completed! Found {len(results)} leads"
        
        job.status = "completed"
        job.completed_at = datetime.utcnow()
        job.successful_extractions = len(results)
        db.commit()
        
        logger.info(f"Scraping job {job_id} completed successfully")
        
    except Exception as e:
        logger.error(f"Error in scraping job {job_id}: {e}")
        active_jobs[job_id]["status"] = "failed"
        active_jobs[job_id]["message"] = f"Error: {str(e)}"
        
        # Update database
        db = next(get_db())
        job = db.query(ScrapingJob).filter(ScrapingJob.id == active_jobs[job_id]["db_id"]).first()
        job.status = "failed"
        job.error_message = str(e)
        db.commit()

def update_progress(job_id: str, progress: int, total: int, successful: int, message: str = None):
    """Update progress for a scraping job."""
    if job_id in active_jobs:
        # Check for cancellation before updating
        if active_jobs[job_id]["status"] == "cancelled":
            return
        
        active_jobs[job_id]["progress"] = progress
        active_jobs[job_id]["total_listings"] = total
        active_jobs[job_id]["successful_extractions"] = successful
        if message:
            active_jobs[job_id]["message"] = message
        else:
            active_jobs[job_id]["message"] = f"Processing {progress}/{total} listings..."

def update_progress_with_lead(job_id: str, progress: int, total: int, successful: int, message: str = None, new_lead: dict = None, db = None):
    """Update progress and save new lead in real-time."""
    if job_id in active_jobs:
        # Check for cancellation before updating
        if active_jobs[job_id]["status"] == "cancelled":
            return
        
        # Track timing phases
        current_time = datetime.utcnow()
        if "loading_start_time" in active_jobs[job_id] and active_jobs[job_id]["loading_start_time"] is None and "loading" in message.lower():
            active_jobs[job_id]["loading_start_time"] = current_time
        elif "scraping_start_time" in active_jobs[job_id] and active_jobs[job_id]["scraping_start_time"] is None and "processing" in message.lower():
            active_jobs[job_id]["scraping_start_time"] = current_time
        
        active_jobs[job_id]["progress"] = progress
        active_jobs[job_id]["total_listings"] = total
        active_jobs[job_id]["successful_extractions"] = successful
        if message:
            active_jobs[job_id]["message"] = message
        else:
            active_jobs[job_id]["message"] = f"Processing {progress}/{total} listings..."
        
        # Calculate timing information
        start_time = active_jobs[job_id]["start_time"]
        total_duration = (current_time - start_time).total_seconds()
        
        loading_duration = None
        if active_jobs[job_id]["loading_start_time"]:
            loading_duration = (active_jobs[job_id]["loading_start_time"] - start_time).total_seconds()
        
        scraping_duration = None
        if active_jobs[job_id]["scraping_start_time"]:
            scraping_duration = (current_time - active_jobs[job_id]["scraping_start_time"]).total_seconds()
        
        # Add timing to message
        timing_info = f" (Total: {total_duration:.1f}s"
        if loading_duration:
            timing_info += f", Loading: {loading_duration:.1f}s"
        if scraping_duration:
            timing_info += f", Scraping: {scraping_duration:.1f}s"
        timing_info += ")"
        
        active_jobs[job_id]["message"] += timing_info
        
        # Update database job statistics
        if db:
            try:
                job = db.query(ScrapingJob).filter(ScrapingJob.id == active_jobs[job_id]["db_id"]).first()
                if job:
                    job.total_listings = total
                    job.successful_extractions = successful
                    job.progress = progress
                    db.commit()
            except Exception as e:
                logger.error(f"Error updating job statistics: {e}")
                db.rollback()
        
        # Save new lead to database if provided
        if new_lead and db:
            try:
                lead = Lead(
                    name=new_lead["name"],
                    phone=new_lead.get("phone", ""),
                    website=new_lead.get("website", ""),
                    email=new_lead.get("email", ""),
                    location=active_jobs[job_id].get("search_term", ""),
                    business_type=active_jobs[job_id].get("search_term", "").split(" in ")[0] if " in " in active_jobs[job_id].get("search_term", "") else "",
                    status="new"
                )
                db.add(lead)
                db.commit()
                logger.info(f"Saved new lead: {new_lead['name']}")
            except Exception as e:
                logger.error(f"Error saving lead: {e}")
                db.rollback()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 
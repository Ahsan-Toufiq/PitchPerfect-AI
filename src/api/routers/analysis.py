"""Analysis API router."""

from fastapi import APIRouter, HTTPException, BackgroundTasks, Query
from pydantic import BaseModel
from typing import Dict, Any, List, Optional
from datetime import datetime

from ...analyzer.orchestrator import AnalysisOrchestrator
from ...database.operations import AnalysisOperations
from ...utils import get_logger

logger = get_logger(__name__)
router = APIRouter()

class AnalysisRequest(BaseModel):
    lead_id: Optional[int] = None
    batch_size: int = 5
    force: bool = False

# Store active analysis jobs
active_jobs: Dict[str, Dict[str, Any]] = {}

@router.post("/start")
async def start_analysis(
    request: AnalysisRequest,
    background_tasks: BackgroundTasks
) -> Dict[str, Any]:
    """Start website analysis."""
    try:
        # Generate job ID
        job_id = f"analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{hash(str(request.lead_id)) % 10000}"
        
        # Initialize job status
        active_jobs[job_id] = {
            "status": "starting",
            "progress": 0,
            "total_analyses": 0,
            "completed_analyses": 0,
            "error": None,
            "started_at": datetime.now().isoformat(),
            "request": request.dict()
        }
        
        # Start analysis in background
        background_tasks.add_task(
            run_analysis_job,
            job_id,
            request.lead_id,
            request.batch_size,
            request.force
        )
        
        return {
            "success": True,
            "data": {
                "job_id": job_id,
                "status": "starting",
                "message": "Analysis job started"
            },
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to start analysis: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/status/{job_id}")
async def get_analysis_status(job_id: str) -> Dict[str, Any]:
    """Get analysis job status."""
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
                "total_analyses": job["total_analyses"],
                "completed_analyses": job["completed_analyses"],
                "error": job["error"],
                "started_at": job["started_at"],
                "request": job["request"]
            },
            "timestamp": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get analysis status: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/jobs")
async def get_active_analysis_jobs() -> Dict[str, Any]:
    """Get all active analysis jobs."""
    try:
        jobs_data = []
        for job_id, job in active_jobs.items():
            jobs_data.append({
                "job_id": job_id,
                "status": job["status"],
                "progress": job["progress"],
                "total_analyses": job["total_analyses"],
                "completed_analyses": job["completed_analyses"],
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
        logger.error(f"Failed to get active analysis jobs: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/results")
async def get_analysis_results(
    lead_id: Optional[int] = Query(None, description="Filter by lead ID"),
    limit: Optional[int] = Query(50, description="Maximum results to return"),
    offset: int = Query(0, description="Number of results to skip")
) -> Dict[str, Any]:
    """Get analysis results."""
    try:
        analysis_ops = AnalysisOperations()
        
        if lead_id:
            # Get specific analysis
            analysis = analysis_ops.get_analysis_by_lead(lead_id)
            if not analysis:
                raise HTTPException(status_code=404, detail="Analysis not found")
            
            return {
                "success": True,
                "data": {
                    "id": analysis.id,
                    "lead_id": analysis.lead_id,
                    "lighthouse_score": analysis.lighthouse_score,
                    "performance_score": analysis.performance_score,
                    "seo_score": analysis.seo_score,
                    "accessibility_score": analysis.accessibility_score,
                    "best_practices_score": analysis.best_practices_score,
                    "seo_issues": analysis.seo_issues,
                    "performance_issues": analysis.performance_issues,
                    "accessibility_issues": analysis.accessibility_issues,
                    "llm_suggestions": analysis.llm_suggestions,
                    "analyzed_at": analysis.analyzed_at.isoformat() if analysis.analyzed_at else None,
                    "analysis_duration": analysis.analysis_duration
                },
                "timestamp": datetime.now().isoformat()
            }
        else:
            # Get recent analyses
            analyses = analysis_ops.get_recent_analyses(limit=limit, offset=offset)
            
            analyses_data = []
            for analysis in analyses:
                analyses_data.append({
                    "id": analysis.id,
                    "lead_id": analysis.lead_id,
                    "lead_name": analysis.lead_name,
                    "lighthouse_score": analysis.lighthouse_score,
                    "performance_score": analysis.performance_score,
                    "seo_score": analysis.seo_score,
                    "accessibility_score": analysis.accessibility_score,
                    "best_practices_score": analysis.best_practices_score,
                    "analyzed_at": analysis.analyzed_at.isoformat() if analysis.analyzed_at else None
                })
            
            return {
                "success": True,
                "data": analyses_data,
                "count": len(analyses_data),
                "timestamp": datetime.now().isoformat()
            }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get analysis results: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/stats")
async def get_analysis_stats() -> Dict[str, Any]:
    """Get analysis statistics."""
    try:
        analysis_ops = AnalysisOperations()
        stats = analysis_ops.get_analysis_statistics()
        
        return {
            "success": True,
            "data": stats,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to get analysis stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))

async def run_analysis_job(
    job_id: str,
    lead_id: Optional[int],
    batch_size: int,
    force: bool
):
    """Run analysis job in background."""
    try:
        # Update job status
        active_jobs[job_id]["status"] = "running"
        
        # Initialize analyzer
        analyzer = AnalysisOrchestrator()
        
        if lead_id:
            # Analyze specific lead
            active_jobs[job_id]["total_analyses"] = 1
            active_jobs[job_id]["progress"] = 50
            
            result = analyzer.analyze_lead(lead_id, force=force)
            
            if result:
                active_jobs[job_id]["status"] = "completed"
                active_jobs[job_id]["completed_analyses"] = 1
                active_jobs[job_id]["progress"] = 100
            else:
                active_jobs[job_id]["status"] = "failed"
                active_jobs[job_id]["error"] = "Analysis failed"
        else:
            # Analyze pending leads
            from ...database.operations import LeadOperations
            lead_ops = LeadOperations()
            pending_leads = lead_ops.get_leads_for_analysis()
            
            active_jobs[job_id]["total_analyses"] = len(pending_leads)
            
            if not pending_leads:
                active_jobs[job_id]["status"] = "completed"
                active_jobs[job_id]["progress"] = 100
                return
            
            # Analyze in batches
            completed = 0
            for i in range(0, len(pending_leads), batch_size):
                if active_jobs[job_id]["status"] == "cancelled":
                    break
                
                batch = pending_leads[i:i + batch_size]
                for lead in batch:
                    if active_jobs[job_id]["status"] == "cancelled":
                        break
                    
                    try:
                        analyzer.analyze_lead(lead.id, force=force)
                        completed += 1
                        active_jobs[job_id]["completed_analyses"] = completed
                        active_jobs[job_id]["progress"] = int((completed / len(pending_leads)) * 100)
                    except Exception as e:
                        logger.error(f"Failed to analyze lead {lead.id}: {e}")
            
            active_jobs[job_id]["status"] = "completed"
            active_jobs[job_id]["progress"] = 100
        
        logger.info(f"Analysis job {job_id} completed")
        
    except Exception as e:
        logger.error(f"Analysis job {job_id} failed: {e}")
        active_jobs[job_id]["status"] = "failed"
        active_jobs[job_id]["error"] = str(e) 
"""FastAPI application for PitchPerfect AI."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pathlib import Path

from .routers import leads, analysis, emails, dashboard, scraping
from ..config import get_settings
from ..utils import get_logger

logger = get_logger(__name__)

# Create FastAPI app
app = FastAPI(
    title="PitchPerfect AI API",
    description="API for automated lead generation and outreach system",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc"
)

# Add CORS middleware for React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],  # React dev servers
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(dashboard.router, prefix="/api/dashboard", tags=["dashboard"])
app.include_router(leads.router, prefix="/api/leads", tags=["leads"])
app.include_router(scraping.router, prefix="/api/scraping", tags=["scraping"])
app.include_router(analysis.router, prefix="/api/analysis", tags=["analysis"])
app.include_router(emails.router, prefix="/api/emails", tags=["emails"])

@app.on_event("startup")
async def startup_event():
    """Initialize application on startup."""
    logger.info("Starting PitchPerfect AI API")
    
    # Initialize database
    from ..database.operations import initialize_database
    initialize_database()
    
    # Validate configuration
    settings = get_settings()
    if not settings.is_email_configured():
        logger.warning("Gmail SMTP not configured. Email sending will be disabled.")
    if not settings.is_ollama_configured():
        logger.warning("Ollama LLM not configured. AI analysis will be limited.")

@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "PitchPerfect AI API"}

@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "PitchPerfect AI API",
        "docs": "/api/docs",
        "health": "/api/health"
    } 
"""Database layer for PitchPerfect AI."""

from .models import init_db, Lead, WebsiteAnalysis, EmailCampaign
from .operations import (
    LeadOperations, AnalysisOperations, EmailOperations,
    initialize_database, get_dashboard_data
)

__all__ = [
    "init_db", "Lead", "WebsiteAnalysis", "EmailCampaign",
    "LeadOperations", "AnalysisOperations", "EmailOperations",
    "initialize_database", "get_dashboard_data"
] 
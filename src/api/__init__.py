"""API module for PitchPerfect AI."""

from .main import app
from .routers import leads, analysis, emails, dashboard, scraping

__all__ = ["app"] 
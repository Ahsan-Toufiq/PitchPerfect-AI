"""Orchestrator for website analysis operations."""

from typing import List, Optional, Dict, Any
from datetime import datetime
import asyncio

from ..database.operations import AnalysisOperations, LeadOperations
from ..database.models import Lead, WebsiteAnalysis
from ..utils import get_logger
from .lighthouse import LighthouseAnalyzer
from .llm_analyzer import LLMAnalyzer

logger = get_logger(__name__)


class AnalysisOrchestrator:
    """Orchestrator for website analysis operations."""
    
    def __init__(self):
        """Initialize the analysis orchestrator."""
        self.lighthouse_analyzer = LighthouseAnalyzer()
        self.llm_analyzer = LLMAnalyzer()
        self.logger = get_logger(__name__)
    
    def analyze_lead(self, lead_id: int, force: bool = False) -> Optional[WebsiteAnalysis]:
        """Analyze a specific lead's website.
        
        Args:
            lead_id: Lead ID to analyze
            force: Force re-analysis even if already analyzed
            
        Returns:
            WebsiteAnalysis object or None if failed
        """
        try:
            # Get lead
            lead = LeadOperations.get_lead(lead_id)
            if not lead:
                self.logger.error(f"Lead {lead_id} not found")
                return None
            
            if not lead.website:
                self.logger.warning(f"Lead {lead_id} has no website")
                return None
            
            # Check if already analyzed (unless force)
            if not force:
                existing_analysis = AnalysisOperations.get_analysis_by_lead(lead_id)
                if existing_analysis:
                    self.logger.info(f"Lead {lead_id} already analyzed")
                    return existing_analysis
            
            self.logger.info(f"Starting analysis for lead {lead_id}: {lead.name}")
            
            # Run Lighthouse analysis
            lighthouse_results = self.lighthouse_analyzer.analyze_website(lead.website)
            
            if not lighthouse_results:
                self.logger.error(f"Lighthouse analysis failed for {lead.website}")
                return None
            
            # Run LLM analysis
            llm_suggestions = self.llm_analyzer.analyze_website(
                lead.website, 
                lighthouse_results
            )
            
            # Create analysis record
            analysis_data = {
                'lead_id': lead_id,
                'lighthouse_score': lighthouse_results.get('lighthouse_score'),
                'performance_score': lighthouse_results.get('performance_score'),
                'seo_score': lighthouse_results.get('seo_score'),
                'accessibility_score': lighthouse_results.get('accessibility_score'),
                'best_practices_score': lighthouse_results.get('best_practices_score'),
                'seo_issues': lighthouse_results.get('seo_issues'),
                'performance_issues': lighthouse_results.get('performance_issues'),
                'accessibility_issues': lighthouse_results.get('accessibility_issues'),
                'llm_suggestions': llm_suggestions,
                'analysis_duration': lighthouse_results.get('duration', 0),
                'raw_lighthouse_data': lighthouse_results.get('raw_data')
            }
            
            analysis_id = AnalysisOperations.create_analysis(analysis_data)
            
            self.logger.info(f"Analysis completed for lead {lead_id}")
            return AnalysisOperations.get_analysis_by_lead(lead_id)
            
        except Exception as e:
            self.logger.error(f"Analysis failed for lead {lead_id}: {e}")
            return None
    
    def analyze_pending_leads(self, batch_size: int = 5, force: bool = False) -> int:
        """Analyze all pending leads.
        
        Args:
            batch_size: Number of concurrent analyses
            force: Force re-analysis of already analyzed leads
            
        Returns:
            Number of analyses completed
        """
        try:
            # Get leads that need analysis
            if force:
                leads = LeadOperations.search_leads(has_website=True)
            else:
                leads = LeadOperations.get_leads_for_analysis()
            
            if not leads:
                self.logger.info("No leads need analysis")
                return 0
            
            self.logger.info(f"Starting analysis of {len(leads)} leads")
            
            completed = 0
            for lead in leads:
                try:
                    result = self.analyze_lead(lead.id, force=force)
                    if result:
                        completed += 1
                except Exception as e:
                    self.logger.error(f"Failed to analyze lead {lead.id}: {e}")
            
            self.logger.info(f"Analysis completed: {completed}/{len(leads)} leads")
            return completed
            
        except Exception as e:
            self.logger.error(f"Batch analysis failed: {e}")
            return 0 
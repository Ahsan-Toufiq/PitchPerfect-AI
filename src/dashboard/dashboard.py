"""Dashboard for PitchPerfect AI system monitoring."""

from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import json

from ..config import get_settings
from ..utils import get_logger, LoggerMixin
from ..database.operations import LeadOperations, EmailOperations, AnalysisOperations
from ..email_system import EmailSender
from ..scraper import ScrapingOrchestrator
from ..analyzer import LLMAnalyzer


class Dashboard(LoggerMixin):
    """Dashboard for monitoring PitchPerfect AI system."""
    
    def __init__(self):
        """Initialize dashboard."""
        self.settings = get_settings()
        self.lead_ops = LeadOperations()
        self.email_ops = EmailOperations()
        self.analysis_ops = AnalysisOperations()
        self.email_sender = EmailSender()
        self.scraping_orchestrator = ScrapingOrchestrator()
        self.llm_analyzer = LLMAnalyzer()
        
        self.logger.info("Dashboard initialized")
    
    def get_system_overview(self) -> Dict[str, Any]:
        """Get comprehensive system overview.
        
        Returns:
            Dictionary with system statistics
        """
        try:
            from ..database.operations import find_leads_needing_analysis
            total_leads = self.lead_ops.get_lead_statistics().get('total_leads', 0)
            total_emails = self.email_ops.get_email_statistics().get('total_campaigns', 0)
            total_analyses = self.analysis_ops.get_analysis_statistics().get('total_analyses', 0)
            recent_leads = 0
            recent_emails = 0
            email_stats = self.email_sender.get_email_stats()
            system_status = self.get_system_status()
            return {
                'database': {
                    'total_leads': total_leads,
                    'total_emails': total_emails,
                    'total_analyses': total_analyses,
                    'recent_leads': recent_leads,
                    'recent_emails': recent_emails
                },
                'email_system': email_stats,
                'system_status': system_status,
                'last_updated': datetime.now().isoformat()
            }
        except Exception as e:
            self.logger.error(f"Error getting system overview: {e}")
            return {
                'error': str(e),
                'last_updated': datetime.now().isoformat()
            }
    
    def get_lead_statistics(self) -> Dict[str, Any]:
        """Get lead-related statistics.
        
        Returns:
            Dictionary with lead statistics
        """
        try:
            stats = self.lead_ops.get_lead_statistics()
            total_leads = stats.get('total_leads', 0)
            by_source = stats.get('source_breakdown', {})
            by_category = stats.get('status_breakdown', {})
            recent_leads = []
            return {
                'total_leads': total_leads,
                'by_source': by_source,
                'by_category': by_category,
                'recent_leads': recent_leads
            }
        except Exception as e:
            self.logger.error(f"Error getting lead statistics: {e}")
            return {'error': str(e)}
    
    def get_email_statistics(self) -> Dict[str, Any]:
        """Get email-related statistics.
        
        Returns:
            Dictionary with email statistics
        """
        try:
            email_stats = self.email_sender.get_email_stats()
            recent_emails = []
            template_usage = {}
            return {
                **email_stats,
                'recent_emails': [],
                'template_usage': {}
            }
        except Exception as e:
            self.logger.error(f"Error getting email statistics: {e}")
            return {'error': str(e)}
    
    def get_analysis_statistics(self) -> Dict[str, Any]:
        """Get analysis-related statistics.
        
        Returns:
            Dictionary with analysis statistics
        """
        try:
            stats = self.analysis_ops.get_analysis_statistics()
            total_analyses = stats.get('total_analyses', 0)
            score_distributions = {
                'seo_scores': [],
                'performance_scores': []
            }
            recent_analyses = []
            return {
                'total_analyses': total_analyses,
                'score_distributions': score_distributions,
                'recent_analyses': recent_analyses
            }
        except Exception as e:
            self.logger.error(f"Error getting analysis statistics: {e}")
            return {'error': str(e)}
    
    def get_system_status(self) -> Dict[str, Any]:
        """Get system component status.
        
        Returns:
            Dictionary with system status
        """
        try:
            email_test = self.email_sender.test_email_system()
            db_status = {
                'leads': True,
                'emails': True,
                'analyses': True
            }
            llm_status = self.llm_analyzer.test_connection()
            return {
                'email_system': email_test,
                'database': db_status,
                'llm_analyzer': llm_status,
                'overall_status': all([
                    email_test['overall_status'],
                    all(db_status.values()),
                    llm_status
                ])
            }
        except Exception as e:
            self.logger.error(f"Error getting system status: {e}")
            return {'error': str(e)}
    
    def get_pipeline_progress(self) -> Dict[str, Any]:
        """Get pipeline execution progress.
        
        Returns:
            Dictionary with pipeline progress
        """
        try:
            from ..database.operations import find_leads_needing_analysis, find_leads_ready_for_email
            leads_without_analysis = find_leads_needing_analysis()
            
            analyses_without_emails = []  # Not implemented, so leave empty
            
            leads_ready_for_email = find_leads_ready_for_email()
            
            return {
                'leads_without_analysis': len(leads_without_analysis),
                'analyses_without_emails': len(analyses_without_emails),
                'leads_ready_for_email': len(leads_ready_for_email),
                'pipeline_stages': {
                    'scraped_leads': self.lead_ops.get_lead_statistics().get('total_leads', 0),
                    'analyzed_leads': self.analysis_ops.get_analysis_statistics().get('total_analyses', 0),
                    'emailed_leads': self.email_ops.get_email_statistics().get('status_breakdown', {}).get('sent', 0)
                }
            }
            
        except Exception as e:
            self.logger.error(f"Error getting pipeline progress: {e}")
            return {'error': str(e)}
    
    def export_dashboard_data(self, format: str = 'json') -> str:
        """Export dashboard data in specified format.
        
        Args:
            format: Export format ('json' or 'csv')
            
        Returns:
            Exported data as string
        """
        try:
            data = {
                'system_overview': self.get_system_overview(),
                'lead_statistics': self.get_lead_statistics(),
                'email_statistics': self.get_email_statistics(),
                'analysis_statistics': self.get_analysis_statistics(),
                'system_status': self.get_system_status(),
                'pipeline_progress': self.get_pipeline_progress(),
                'exported_at': datetime.now().isoformat()
            }
            
            if format.lower() == 'json':
                return json.dumps(data, indent=2)
            elif format.lower() == 'csv':
                # Simple CSV export of key metrics
                csv_lines = [
                    'Metric,Value',
                    f'Total Leads,{data["system_overview"]["database"]["total_leads"]}',
                    f'Total Emails,{data["system_overview"]["database"]["total_emails"]}',
                    f'Total Analyses,{data["system_overview"]["database"]["total_analyses"]}',
                    f'Recent Leads,{data["system_overview"]["database"]["recent_leads"]}',
                    f'Recent Emails,{data["system_overview"]["database"]["recent_emails"]}'
                ]
                return '\n'.join(csv_lines)
            else:
                raise ValueError(f"Unsupported format: {format}")
                
        except Exception as e:
            self.logger.error(f"Error exporting dashboard data: {e}")
            return f"Error: {str(e)}"
    
    def get_recommendations(self) -> List[Dict[str, Any]]:
        """Get system recommendations based on current state.
        
        Returns:
            List of recommendation dictionaries
        """
        recommendations = []
        
        try:
            from ..database.operations import find_leads_needing_analysis, find_leads_ready_for_email
            leads_without_analysis = find_leads_needing_analysis()
            if leads_without_analysis:
                recommendations.append({
                    'type': 'analysis_needed',
                    'message': f'Run analysis on {len(leads_without_analysis)} leads',
                    'priority': 'high',
                    'action': 'analyze_leads'
                })
            
            analyses_without_emails = []  # Not implemented
            if analyses_without_emails:
                recommendations.append({
                    'type': 'email_needed',
                    'message': f'Send emails to {len(analyses_without_emails)} analyzed leads',
                    'priority': 'medium',
                    'action': 'send_emails'
                })
            
            # Check email system status
            email_stats = self.email_sender.get_email_stats()
            if email_stats['smtp']['remaining_today'] == 0:
                recommendations.append({
                    'type': 'daily_limit_reached',
                    'message': 'Daily email limit reached',
                    'priority': 'low',
                    'action': 'wait_for_reset'
                })
            
            # Check system health
            system_status = self.get_system_status()
            if not system_status.get('overall_status', True):
                recommendations.append({
                    'type': 'system_issue',
                    'message': 'System components need attention',
                    'priority': 'high',
                    'action': 'check_system'
                })
            
        except Exception as e:
            self.logger.error(f"Error getting recommendations: {e}")
            recommendations.append({
                'type': 'error',
                'message': f'Error generating recommendations: {str(e)}',
                'priority': 'high',
                'action': 'check_logs'
            })
        
        return recommendations 
"""Email sender for PitchPerfect AI."""

from typing import List, Dict, Any, Optional
from datetime import datetime
import time

from ..config import get_settings
from ..utils import get_logger, LoggerMixin
from ..database.operations import Lead, WebsiteAnalysis, EmailOperations, EmailStatus
from .smtp_client import SMTPClient, SMTPError
from .template_engine import EmailTemplateEngine, TemplateError


class EmailSenderError(Exception):
    """Custom email sender error."""
    pass


class EmailSender(LoggerMixin):
    """Email sender that coordinates template generation and SMTP sending."""
    
    def __init__(self):
        """Initialize email sender."""
        self.settings = get_settings()
        self.smtp_client = SMTPClient()
        self.template_engine = EmailTemplateEngine()
        self.email_ops = EmailOperations()
        
        self.logger.info("Email sender initialized")
    
    def send_single_email(
        self,
        lead: Lead,
        template_type: str = 'website_improvement',
        analysis: Optional[WebsiteAnalysis] = None,
        custom_subject: Optional[str] = None,
        custom_body: Optional[str] = None
    ) -> Dict[str, Any]:
        """Send a single email to a lead.
        
        Args:
            lead: Lead to send email to
            template_type: Template type to use
            analysis: Website analysis data (optional)
            custom_subject: Custom subject line (overrides template)
            custom_body: Custom body content (overrides template)
            
        Returns:
            Dictionary with send results
        """
        try:
            # Generate email content
            if custom_subject and custom_body:
                subject = custom_subject
                body = custom_body
                template_type = 'custom'
            else:
                email_data = self.template_engine.generate_email(lead, template_type, analysis)
                subject = email_data['subject']
                body = email_data['body']
            
            # Send email
            success = self.smtp_client.send_email(
                to_email=lead.email,
                subject=subject,
                body=body,
                from_name=self.settings.email_from_name
            )
            
            # Record in database
            email_record = self.email_ops.create_email(
                lead_id=lead.id,
                subject=subject,
                body=body,
                template_type=template_type,
                status=EmailStatus.SENT if success else EmailStatus.FAILED,
                sent_at=datetime.now() if success else None
            )
            
            result = {
                'success': success,
                'lead_id': lead.id,
                'email_id': email_record.id if email_record else None,
                'business_name': lead.name,
                'to_email': lead.email,
                'template_type': template_type,
                'sent_at': datetime.now().isoformat() if success else None
            }
            
            if success:
                self.logger.info(f"Email sent successfully to {lead.name} ({lead.email})")
            else:
                self.logger.warning(f"Failed to send email to {lead.name} ({lead.email})")
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error sending email to {lead.name}: {e}")
            return {
                'success': False,
                'lead_id': lead.id,
                'error': str(e),
                'business_name': lead.name,
                'to_email': lead.email
            }
    
    def send_bulk_emails(
        self,
        leads: List[Lead],
        template_type: str = 'website_improvement',
        analyses: Optional[Dict[int, WebsiteAnalysis]] = None,
        delay_between: float = 2.0,
        max_emails: Optional[int] = None
    ) -> Dict[str, Any]:
        """Send emails to multiple leads.
        
        Args:
            leads: List of leads to email
            template_type: Template type to use
            analyses: Dictionary mapping lead_id to analysis
            delay_between: Delay between emails in seconds
            max_emails: Maximum number of emails to send (optional)
            
        Returns:
            Dictionary with bulk send results
        """
        results = {
            'total_leads': len(leads),
            'emails_sent': 0,
            'emails_failed': 0,
            'emails_skipped': 0,
            'errors': [],
            'successful_leads': [],
            'failed_leads': []
        }
        
        self.logger.info(f"Starting bulk email send: {len(leads)} leads")
        
        # Limit emails if specified
        if max_emails:
            leads = leads[:max_emails]
            self.logger.info(f"Limited to {max_emails} emails")
        
        for i, lead in enumerate(leads):
            try:
                # Get analysis for this lead if available
                analysis = analyses.get(lead.id) if analyses else None
                
                # Send email
                result = self.send_single_email(lead, template_type, analysis)
                
                if result['success']:
                    results['emails_sent'] += 1
                    results['successful_leads'].append({
                        'lead_id': lead.id,
                        'business_name': lead.name,
                        'email': lead.email
                    })
                else:
                    results['emails_failed'] += 1
                    results['failed_leads'].append({
                        'lead_id': lead.id,
                        'business_name': lead.name,
                        'email': lead.email,
                        'error': result.get('error', 'Unknown error')
                    })
                
                # Progress logging
                if (i + 1) % 10 == 0:
                    self.logger.info(f"Progress: {i + 1}/{len(leads)} emails processed")
                
                # Delay between emails
                if i < len(leads) - 1:  # Don't delay after last email
                    time.sleep(delay_between)
                    
            except Exception as e:
                results['emails_failed'] += 1
                error_msg = f"Lead {lead.id} ({lead.name}): {str(e)}"
                results['errors'].append(error_msg)
                self.logger.error(error_msg)
        
        self.logger.info(f"Bulk email completed: {results['emails_sent']} sent, {results['emails_failed']} failed")
        return results
    
    def send_analysis_based_emails(
        self,
        leads: List[Lead],
        analyses: Dict[int, WebsiteAnalysis],
        delay_between: float = 2.0
    ) -> Dict[str, Any]:
        """Send emails based on website analysis results.
        
        Args:
            leads: List of leads to email
            analyses: Dictionary mapping lead_id to analysis
            delay_between: Delay between emails in seconds
            
        Returns:
            Dictionary with send results
        """
        results = {
            'total_leads': len(leads),
            'emails_sent': 0,
            'emails_failed': 0,
            'template_usage': {
                'website_improvement': 0,
                'seo_optimization': 0,
                'performance_boost': 0,
                'general_outreach': 0
            }
        }
        
        self.logger.info(f"Starting analysis-based email send: {len(leads)} leads")
        
        for i, lead in enumerate(leads):
            try:
                analysis = analyses.get(lead.id)
                
                # Choose template based on analysis
                template_type = self._select_template_by_analysis(analysis)
                results['template_usage'][template_type] += 1
                
                # Send email
                result = self.send_single_email(lead, template_type, analysis)
                
                if result['success']:
                    results['emails_sent'] += 1
                else:
                    results['emails_failed'] += 1
                
                # Progress logging
                if (i + 1) % 10 == 0:
                    self.logger.info(f"Progress: {i + 1}/{len(leads)} emails processed")
                
                # Delay between emails
                if i < len(leads) - 1:
                    time.sleep(delay_between)
                    
            except Exception as e:
                results['emails_failed'] += 1
                self.logger.error(f"Error sending analysis-based email to {lead.name}: {e}")
        
        self.logger.info(f"Analysis-based emails completed: {results['emails_sent']} sent, {results['emails_failed']} failed")
        return results
    
    def _select_template_by_analysis(self, analysis: Optional[WebsiteAnalysis]) -> str:
        """Select email template based on website analysis.
        
        Args:
            analysis: Website analysis data
            
        Returns:
            Template type to use
        """
        if not analysis:
            return 'general_outreach'
        
        # Prioritize based on scores
        if analysis.seo_score and analysis.seo_score < 70:
            return 'seo_optimization'
        elif analysis.performance_score and analysis.performance_score < 70:
            return 'performance_boost'
        elif analysis.seo_issues or analysis.performance_issues:
            return 'website_improvement'
        else:
            return 'general_outreach'
    
    def test_email_system(self) -> Dict[str, Any]:
        """Test the complete email system.
        
        Returns:
            Dictionary with test results
        """
        results = {
            'smtp_connection': False,
            'template_engine': False,
            'database_connection': False,
            'overall_status': False
        }
        
        # Test SMTP connection
        try:
            results['smtp_connection'] = self.smtp_client.test_connection()
        except Exception as e:
            self.logger.error(f"SMTP test failed: {e}")
        
        # Test template engine
        try:
            templates = self.template_engine.get_available_templates()
            results['template_engine'] = len(templates) > 0
        except Exception as e:
            self.logger.error(f"Template engine test failed: {e}")
        
        # Test database connection
        try:
            # Try to get email statistics
            stats = self.email_ops.get_email_statistics()
            results['database_connection'] = 'total_campaigns' in stats
        except Exception as e:
            self.logger.error(f"Database test failed: {e}")
        
        # Overall status
        results['overall_status'] = all([
            results['smtp_connection'],
            results['template_engine'],
            results['database_connection']
        ])
        
        return results
    
    def get_email_stats(self) -> Dict[str, Any]:
        """Get email system statistics.
        
        Returns:
            Dictionary with email stats
        """
        # Get database stats
        stats = self.email_ops.get_email_statistics()
        total_emails = stats.get('total_campaigns', 0)
        status_breakdown = stats.get('status_breakdown', {})
        sent_emails = status_breakdown.get('sent', 0)
        failed_emails = status_breakdown.get('failed', 0)
        
        # Get SMTP stats
        smtp_stats = self.smtp_client.get_daily_stats()
        rate_limit_stats = self.smtp_client.get_rate_limit_info()
        
        return {
            'database': {
                'total_emails': total_emails,
                'sent_emails': sent_emails,
                'failed_emails': failed_emails,
                'success_rate': (sent_emails / total_emails * 100) if total_emails > 0 else 0
            },
            'smtp': smtp_stats,
            'rate_limiting': rate_limit_stats,
            'templates': {
                'available_templates': self.template_engine.get_available_templates()
            }
        }
    
    def preview_email(
        self,
        lead: Lead,
        template_type: str = 'website_improvement',
        analysis: Optional[WebsiteAnalysis] = None
    ) -> Dict[str, str]:
        """Preview an email without sending it.
        
        Args:
            lead: Lead data
            template_type: Template type to preview
            analysis: Website analysis data (optional)
            
        Returns:
            Dictionary with subject and body preview
        """
        return self.template_engine.generate_email(lead, template_type, analysis)
    
    def validate_email_address(self, email: str) -> bool:
        """Validate an email address.
        
        Args:
            email: Email address to validate
            
        Returns:
            True if email is valid
        """
        from ..utils import validate_email
        validation = validate_email(email)
        return validation.is_valid 
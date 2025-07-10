"""Orchestrator for email system operations."""

from typing import List, Optional, Dict, Any
from datetime import datetime

from ..database.operations import EmailOperations, LeadOperations
from ..database.models import Lead, EmailCampaign
from ..utils import get_logger
from .sender import EmailSender
from .template_engine import EmailTemplateEngine

logger = get_logger(__name__)


class EmailOrchestrator:
    """Orchestrator for email system operations."""
    
    def __init__(self):
        """Initialize the email orchestrator."""
        self.email_sender = EmailSender()
        self.template_engine = EmailTemplateEngine()
        self.logger = get_logger(__name__)
    
    def send_email_to_lead(self, lead_id: int, template: Optional[str] = None, 
                          dry_run: bool = True) -> bool:
        """Send email to a specific lead.
        
        Args:
            lead_id: Lead ID to send email to
            template: Email template to use
            dry_run: If True, don't actually send the email
            
        Returns:
            True if email was sent successfully
        """
        try:
            # Get lead
            lead = LeadOperations.get_lead(lead_id)
            if not lead:
                self.logger.error(f"Lead {lead_id} not found")
                return False
            
            if not lead.email:
                self.logger.warning(f"Lead {lead_id} has no email address")
                return False
            
            # Check if already sent
            existing_campaign = EmailOperations.get_email_campaign(lead_id)
            if existing_campaign:
                self.logger.info(f"Email already sent to lead {lead_id}")
                return True
            
            # Generate email content
            email_content = self.template_engine.generate_email(
                lead, template=template
            )
            
            if not email_content:
                self.logger.error(f"Failed to generate email content for lead {lead_id}")
                return False
            
            # Create campaign record
            campaign_data = {
                'lead_id': lead_id,
                'subject': email_content.get('subject', 'Website Improvement Opportunity'),
                'email_content': email_content.get('body', ''),
                'email_html': email_content.get('html', ''),
                'template_used': template or 'default',
                'personalization_data': email_content.get('personalization', {})
            }
            
            campaign_id = EmailOperations.create_email_campaign(campaign_data)
            
            if dry_run:
                self.logger.info(f"DRY RUN: Would send email to {lead.email}")
                return True
            
            # Send email
            success = self.email_sender.send_email(
                to_email=lead.email,
                subject=campaign_data['subject'],
                body=campaign_data['email_content'],
                html=campaign_data['email_html']
            )
            
            if success:
                # Update campaign status
                EmailOperations.update_email_status(
                    campaign_id, 'sent', sent_at=datetime.now()
                )
                self.logger.info(f"Email sent successfully to {lead.email}")
                return True
            else:
                # Update campaign status
                EmailOperations.update_email_status(
                    campaign_id, 'failed'
                )
                self.logger.error(f"Failed to send email to {lead.email}")
                return False
                
        except Exception as e:
            self.logger.error(f"Email sending failed for lead {lead_id}: {e}")
            return False
    
    def send_campaign_emails(self, dry_run: bool = True, max_emails: int = 50) -> int:
        """Send emails to all leads ready for email outreach.
        
        Args:
            dry_run: If True, don't actually send emails
            max_emails: Maximum number of emails to send
            
        Returns:
            Number of emails sent
        """
        try:
            # Get leads ready for email
            leads = LeadOperations.get_leads_for_email()
            
            if not leads:
                self.logger.info("No leads ready for email outreach")
                return 0
            
            # Limit to max_emails
            leads = leads[:max_emails]
            
            self.logger.info(f"Starting email campaign for {len(leads)} leads")
            
            sent_count = 0
            for lead in leads:
                try:
                    success = self.send_email_to_lead(lead.id, dry_run=dry_run)
                    if success:
                        sent_count += 1
                except Exception as e:
                    self.logger.error(f"Failed to send email to lead {lead.id}: {e}")
            
            self.logger.info(f"Email campaign completed: {sent_count}/{len(leads)} emails sent")
            return sent_count
            
        except Exception as e:
            self.logger.error(f"Email campaign failed: {e}")
            return 0 
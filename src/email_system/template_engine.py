"""Email template engine for PitchPerfect AI."""

import re
from typing import Dict, Any, Optional, List
from datetime import datetime

from ..config import get_settings
from ..utils import get_logger, LoggerMixin
from ..database.operations import Lead, WebsiteAnalysis


class TemplateError(Exception):
    """Custom template error."""
    pass


class EmailTemplateEngine(LoggerMixin):
    """Email template engine for generating personalized cold emails."""
    
    def __init__(self):
        """Initialize template engine."""
        self.settings = get_settings()
        self.templates = self._load_templates()
        
        self.logger.info("Email template engine initialized")
    
    def _load_templates(self) -> Dict[str, Dict[str, str]]:
        """Load email templates.
        
        Returns:
            Dictionary of template categories and their content
        """
        return {
            'website_improvement': {
                'subject': 'Quick question about {business_name}',
                'body': self._get_website_improvement_template()
            },
            'seo_optimization': {
                'subject': 'Found {business_name} online - quick question',
                'body': self._get_seo_optimization_template()
            },
            'performance_boost': {
                'subject': 'Helping {business_name} get more customers',
                'body': self._get_performance_boost_template()
            },
            'general_outreach': {
                'subject': 'Quick question about {business_name}',
                'body': self._get_general_outreach_template()
            }
        }
    
    def _get_website_improvement_template(self) -> str:
        """Get website improvement email template.
        
        Returns:
            Template string with placeholders
        """
        return """Hi {contact_name},

I recently came across {business_name} and noticed your website could be getting more traffic and customers.

Our analysis found some quick wins that could help {business_name}:
- {main_issue}
- {secondary_issue}
- {third_issue}

These improvements typically lead to {expected_benefit} for businesses like yours.

Would you be interested in a brief conversation about how we could help {business_name} get more customers online?

Best regards,
{from_name}

P.S. Reply STOP to unsubscribe from future emails."""
    
    def _get_seo_optimization_template(self) -> str:
        """Get SEO optimization email template.
        
        Returns:
            Template string with placeholders
        """
        return """Hi {contact_name},

I was researching {business_category} businesses and found {business_name}.

Your website has some great content, but I noticed a few opportunities to help more customers find you online:
- {seo_issue_1}
- {seo_issue_2}
- {seo_issue_3}

These changes could help {business_name} appear higher in search results and attract more local customers.

Would you be open to a quick chat about improving your online visibility?

Best regards,
{from_name}

P.S. Reply STOP to unsubscribe from future emails."""
    
    def _get_performance_boost_template(self) -> str:
        """Get performance boost email template.
        
        Returns:
            Template string with placeholders
        """
        return """Hi {contact_name},

I came across {business_name} and was impressed by your {business_category} services.

However, I noticed your website might be missing some customers due to:
- {performance_issue_1}
- {performance_issue_2}
- {performance_issue_3}

These improvements typically help businesses like yours convert more visitors into customers.

Would you be interested in a brief discussion about optimizing {business_name}'s online performance?

Best regards,
{from_name}

P.S. Reply STOP to unsubscribe from future emails."""
    
    def _get_general_outreach_template(self) -> str:
        """Get general outreach email template.
        
        Returns:
            Template string with placeholders
        """
        return """Hi {contact_name},

I recently discovered {business_name} and was impressed by your {business_category} services.

I help businesses like yours improve their online presence to attract more customers. Based on what I've seen, there are some opportunities to help {business_name} get more visibility and customers online.

Would you be interested in a quick conversation about how we could help {business_name} grow?

Best regards,
{from_name}

P.S. Reply STOP to unsubscribe from future emails."""
    
    def _extract_analysis_insights(self, analysis: Optional[WebsiteAnalysis]) -> Dict[str, str]:
        """Extract insights from website analysis for email personalization.
        
        Args:
            analysis: Website analysis data
            
        Returns:
            Dictionary of insights for template variables
        """
        insights = {
            'main_issue': 'improve website performance',
            'secondary_issue': 'enhance user experience',
            'third_issue': 'boost search visibility',
            'expected_benefit': 'increased customer inquiries',
            'seo_issue_1': 'optimize for local search',
            'seo_issue_2': 'improve page loading speed',
            'seo_issue_3': 'enhance mobile experience',
            'performance_issue_1': 'slow page loading times',
            'performance_issue_2': 'mobile optimization opportunities',
            'performance_issue_3': 'search engine visibility'
        }
        
        if not analysis:
            return insights
        
        # Extract specific issues from analysis
        if analysis.seo_issues:
            seo_issues = analysis.seo_issues.split('\n')[:3]
            for i, issue in enumerate(seo_issues, 1):
                insights[f'seo_issue_{i}'] = issue.strip()
        
        if analysis.performance_issues:
            perf_issues = analysis.performance_issues.split('\n')[:3]
            for i, issue in enumerate(perf_issues, 1):
                insights[f'performance_issue_{i}'] = issue.strip()
        
        # Use scores to determine main focus
        if analysis.seo_score and analysis.seo_score < 70:
            insights['main_issue'] = 'improve search engine visibility'
            insights['expected_benefit'] = 'higher search rankings'
        elif analysis.performance_score and analysis.performance_score < 70:
            insights['main_issue'] = 'speed up website loading'
            insights['expected_benefit'] = 'better user experience'
        
        return insights
    
    def _personalize_content(self, template: str, lead: Lead, analysis: Optional[WebsiteAnalysis] = None) -> str:
        """Personalize email content with lead and analysis data.
        
        Args:
            template: Email template
            lead: Lead data
            analysis: Website analysis (optional)
            
        Returns:
            Personalized email content
        """
        # Basic lead data
        variables = {
            'business_name': lead.name or 'your business',
            'contact_name': self._extract_contact_name(lead.name),
            'business_category': lead.category or 'business',
            'from_name': self.settings.email_from_name or 'PitchPerfect AI'
        }
        
        # Add analysis insights
        if analysis:
            insights = self._extract_analysis_insights(analysis)
            variables.update(insights)
        
        # Replace variables in template
        personalized = template
        for var_name, value in variables.items():
            placeholder = f'{{{var_name}}}'
            personalized = personalized.replace(placeholder, str(value))
        
        return personalized
    
    def _extract_contact_name(self, business_name: str) -> str:
        """Extract contact name from business name.
        
        Args:
            business_name: Full business name
            
        Returns:
            Extracted contact name or generic greeting
        """
        if not business_name:
            return 'there'
        
        # Try to extract owner name from business name
        # Common patterns: "John's Restaurant", "Smith & Co", etc.
        patterns = [
            r"^([A-Z][a-z]+)'s\s+",  # John's Restaurant
            r"^([A-Z][a-z]+)\s+&\s+",  # Smith & Co
            r"^([A-Z][a-z]+)\s+[A-Z]",  # John Smith Restaurant
        ]
        
        for pattern in patterns:
            match = re.search(pattern, business_name)
            if match:
                return match.group(1)
        
        # If no pattern matches, use first word
        words = business_name.split()
        if words:
            return words[0]
        
        return 'there'
    
    def generate_email(
        self,
        lead: Lead,
        template_type: str = 'website_improvement',
        analysis: Optional[WebsiteAnalysis] = None
    ) -> Dict[str, str]:
        """Generate personalized email for a lead.
        
        Args:
            lead: Lead data
            template_type: Type of template to use
            analysis: Website analysis data (optional)
            
        Returns:
            Dictionary with subject and body
        """
        if template_type not in self.templates:
            raise TemplateError(f"Unknown template type: {template_type}")
        
        template = self.templates[template_type]
        
        # Personalize content
        subject = self._personalize_content(template['subject'], lead, analysis)
        body = self._personalize_content(template['body'], lead, analysis)
        
        return {
            'subject': subject,
            'body': body,
            'template_type': template_type
        }
    
    def generate_bulk_emails(
        self,
        leads: List[Lead],
        template_type: str = 'website_improvement',
        analyses: Optional[Dict[int, WebsiteAnalysis]] = None
    ) -> List[Dict[str, Any]]:
        """Generate emails for multiple leads.
        
        Args:
            leads: List of leads
            template_type: Template type to use
            analyses: Dictionary mapping lead_id to analysis (optional)
            
        Returns:
            List of email data dictionaries
        """
        emails = []
        
        for lead in leads:
            try:
                # Get analysis for this lead if available
                analysis = analyses.get(lead.id) if analyses else None
                
                # Generate email
                email_data = self.generate_email(lead, template_type, analysis)
                
                # Add lead data
                email_data.update({
                    'lead_id': lead.id,
                    'to_email': lead.email,
                    'business_name': lead.name,
                    'created_at': datetime.now().isoformat()
                })
                
                emails.append(email_data)
                
            except Exception as e:
                self.logger.error(f"Failed to generate email for lead {lead.id}: {e}")
                continue
        
        self.logger.info(f"Generated {len(emails)} emails from {len(leads)} leads")
        return emails
    
    def get_available_templates(self) -> List[str]:
        """Get list of available template types.
        
        Returns:
            List of template type names
        """
        return list(self.templates.keys())
    
    def preview_template(
        self,
        template_type: str,
        sample_lead: Optional[Lead] = None,
        sample_analysis: Optional[WebsiteAnalysis] = None
    ) -> Dict[str, str]:
        """Preview a template with sample data.
        
        Args:
            template_type: Template type to preview
            sample_lead: Sample lead data
            sample_analysis: Sample analysis data
            
        Returns:
            Dictionary with subject and body preview
        """
        if not sample_lead:
            # Create sample lead
            sample_lead = Lead(
                id=0,
                name="Sample Restaurant",
                email="sample@example.com",
                category="Restaurant",
                source="sample"
            )
        
        return self.generate_email(sample_lead, template_type, sample_analysis)
    
    def validate_template(self, template_type: str) -> bool:
        """Validate that a template type exists and is properly formatted.
        
        Args:
            template_type: Template type to validate
            
        Returns:
            True if template is valid
        """
        if template_type not in self.templates:
            return False
        
        template = self.templates[template_type]
        
        # Check required fields
        required_fields = ['subject', 'body']
        for field in required_fields:
            if field not in template:
                return False
        
        # Check for basic placeholders
        if '{business_name}' not in template['subject']:
            return False
        
        return True 
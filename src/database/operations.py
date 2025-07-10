"""Database operations for PitchPerfect AI."""

from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime, timedelta
from contextlib import contextmanager
from sqlalchemy.orm import Session

from .models import (
    Lead, WebsiteAnalysis, EmailCampaign, 
    LeadStatus, EmailStatus,
    init_db, get_db
)
from ..utils import get_logger, validate_business_data, validate_email
from ..config import get_settings


logger = get_logger(__name__)


class DatabaseError(Exception):
    """Custom database error."""
    pass


class LeadOperations:
    """Database operations for leads."""
    
    @staticmethod
    def create_lead(lead_data: Dict[str, Any]) -> int:
        """Create a new lead.
        
        Args:
            lead_data: Lead data dictionary
            
        Returns:
            ID of created lead
            
        Raises:
            DatabaseError: If creation fails
        """
        # Validate lead data
        validation = validate_business_data(lead_data)
        if not validation.is_valid:
            raise DatabaseError(f"Invalid lead data: {validation.error_message}")
        
        # Use cleaned data
        clean_data = validation.cleaned_value
        
        # Create Lead object
        lead = Lead(
            name=clean_data['name'],
            website=clean_data.get('website'),
            email=clean_data.get('email'),
            location=clean_data.get('location'),
            phone=clean_data.get('phone'),
            business_type=clean_data.get('category'),
            scraped_at=datetime.now(),
            status=clean_data.get('status', 'new'),
            notes=clean_data.get('metadata')
        )
        
        try:
            db = next(get_db())
            db.add(lead)
            db.commit()
            db.refresh(lead)
            
            logger.info(f"Created lead {lead.id}: {lead.name}")
            return lead.id
                
        except Exception as e:
            logger.error(f"Failed to create lead: {e}")
            raise DatabaseError(f"Database error creating lead: {e}")
    
    @staticmethod
    def get_lead(lead_id: int) -> Optional[Lead]:
        """Get lead by ID.
        
        Args:
            lead_id: Lead ID
            
        Returns:
            Lead object or None if not found
        """
        try:
            db = next(get_db())
            lead = db.query(Lead).filter(Lead.id == lead_id).first()
            return lead
                
        except Exception as e:
            logger.error(f"Failed to get lead {lead_id}: {e}")
            raise DatabaseError(f"Database error getting lead: {e}")
    
    @staticmethod
    def update_lead(lead_id: int, updates: Dict[str, Any]) -> bool:
        """Update lead.
        
        Args:
            lead_id: Lead ID
            updates: Dictionary of fields to update
            
        Returns:
            True if updated successfully
        """
        if not updates:
            return True
        
        try:
            db = next(get_db())
            lead = db.query(Lead).filter(Lead.id == lead_id).first()
            
            if not lead:
                return False
            
            # Update fields
            for field, value in updates.items():
                if hasattr(lead, field) and field not in ['id']:
                    setattr(lead, field, value)
            
            db.commit()
            logger.debug(f"Updated lead {lead_id}")
            return True
        
        except Exception as e:
            logger.error(f"Failed to update lead {lead_id}: {e}")
            raise DatabaseError(f"Database error updating lead: {e}")
    
    @staticmethod
    def update_lead_status(lead_id: int, status: str) -> bool:
        """Update lead status.
        
        Args:
            lead_id: Lead ID
            status: New status
            
        Returns:
            True if updated successfully
        """
        return LeadOperations.update_lead(lead_id, {'status': status})
    
    @staticmethod
    def search_leads(
        status: Optional[str] = None,
        source: Optional[str] = None,
        has_email: Optional[bool] = None,
        has_website: Optional[bool] = None,
        limit: Optional[int] = None,
        offset: int = 0
    ) -> List[Lead]:
        """Search leads with filters.
        
        Args:
            status: Filter by status
            source: Filter by source
            has_email: Filter by email presence
            has_website: Filter by website presence
            limit: Maximum results to return
            offset: Number of results to skip
            
        Returns:
            List of Lead objects
        """
        try:
            db = next(get_db())
            query = db.query(Lead)
        
            if status:
                query = query.filter(Lead.status == status)
        
            if has_email is not None:
                if has_email:
                    query = query.filter(Lead.email.isnot(None)).filter(Lead.email != '')
                else:
                    query = query.filter((Lead.email.is_(None)) | (Lead.email == ''))
        
            if has_website is not None:
                if has_website:
                    query = query.filter(Lead.website.isnot(None)).filter(Lead.website != '')
                else:
                    query = query.filter((Lead.website.is_(None)) | (Lead.website == ''))
            
            query = query.order_by(Lead.scraped_at.desc())
            
            if offset:
                query = query.offset(offset)
            if limit:
                query = query.limit(limit)
            
            return query.all()
                
        except Exception as e:
            logger.error(f"Failed to search leads: {e}")
            raise DatabaseError(f"Database error searching leads: {e}")
    
    @staticmethod
    def get_leads_for_analysis() -> List[Lead]:
        """Get leads that need website analysis."""
        return LeadOperations.search_leads(
            status=LeadStatus.NEW.value,
            has_website=True
        )
    
    @staticmethod
    def get_leads_for_email() -> List[Lead]:
        """Get leads ready for email outreach."""
        return LeadOperations.search_leads(
            status=LeadStatus.ANALYZED.value,
            has_email=True
        )
    
    @staticmethod
    def get_lead_statistics() -> Dict[str, Any]:
        """Get lead statistics.
        
        Returns:
            Dictionary with various statistics
        """
        try:
            db = next(get_db())
            
            # Total counts by status
            status_counts = {}
            status_results = db.query(Lead.status, db.func.count(Lead.id)).group_by(Lead.status).all()
            for status, count in status_results:
                status_counts[status] = count
            
            # Total counts
            total_leads = db.query(Lead).count()
            leads_with_email = db.query(Lead).filter(Lead.email.isnot(None)).filter(Lead.email != '').count()
            leads_with_website = db.query(Lead).filter(Lead.website.isnot(None)).filter(Lead.website != '').count()
                
            # Recent activity (last 7 days)
            week_ago = datetime.now() - timedelta(days=7)
            recent_leads = db.query(Lead).filter(Lead.scraped_at >= week_ago).count()
                
            return {
                'total_leads': total_leads,
                'leads_with_email': leads_with_email,
                'leads_with_website': leads_with_website,
                'recent_leads_7d': recent_leads,
                'status_breakdown': status_counts,
                'source_breakdown': {}  # Not implemented in current schema
            }
                
        except Exception as e:
            logger.error(f"Failed to get lead statistics: {e}")
            raise DatabaseError(f"Database error getting statistics: {e}")

    @staticmethod
    def delete_lead(lead_id: int) -> bool:
        """Delete a lead.
        
        Args:
            lead_id: Lead ID
            
        Returns:
            True if deleted successfully
        """
        try:
            db = next(get_db())
            lead = db.query(Lead).filter(Lead.id == lead_id).first()
            
            if not lead:
                return False
            
            db.delete(lead)
            db.commit()
            logger.info(f"Deleted lead {lead_id}")
            return True
                
        except Exception as e:
            logger.error(f"Failed to delete lead {lead_id}: {e}")
            raise DatabaseError(f"Database error deleting lead: {e}")


class AnalysisOperations:
    """Database operations for website analysis."""
    
    @staticmethod
    def create_analysis(analysis_data: Dict[str, Any]) -> int:
        """Create website analysis record.
        
        Args:
            analysis_data: Analysis data dictionary
            
        Returns:
            ID of created analysis
        """
        analysis = WebsiteAnalysis(
            lead_id=analysis_data['lead_id'],
            lighthouse_score=analysis_data.get('lighthouse_score'),
            performance_score=analysis_data.get('performance_score'),
            seo_score=analysis_data.get('seo_score'),
            accessibility_score=analysis_data.get('accessibility_score'),
            best_practices_score=analysis_data.get('best_practices_score'),
            seo_issues=analysis_data.get('seo_issues'),
            performance_issues=analysis_data.get('performance_issues'),
            accessibility_issues=analysis_data.get('accessibility_issues'),
            llm_suggestions=analysis_data.get('llm_suggestions'),
            analysis_duration=analysis_data.get('analysis_duration'),
            raw_lighthouse_data=analysis_data.get('raw_lighthouse_data'),
            analyzed_at=datetime.now()
        )
        
        try:
            with get_database_connection() as conn:
                cursor = conn.execute("""
                    INSERT INTO website_analysis
                    (lead_id, lighthouse_score, performance_score, seo_score,
                     accessibility_score, best_practices_score, seo_issues,
                     performance_issues, accessibility_issues, llm_suggestions,
                     analyzed_at, analysis_duration, raw_lighthouse_data)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    analysis.lead_id, analysis.lighthouse_score,
                    analysis.performance_score, analysis.seo_score,
                    analysis.accessibility_score, analysis.best_practices_score,
                    analysis.seo_issues, analysis.performance_issues,
                    analysis.accessibility_issues, analysis.llm_suggestions,
                    analysis.analyzed_at.isoformat(),
                    analysis.analysis_duration, analysis.raw_lighthouse_data
                ))
                
                analysis_id = cursor.lastrowid
                
                # Update lead status
                LeadOperations.update_lead_status(
                    analysis.lead_id, LeadStatus.ANALYZED.value
                )
                
                logger.info(f"Created analysis {analysis_id} for lead {analysis.lead_id}")
                return analysis_id
                
        except sqlite3.Error as e:
            logger.error(f"Failed to create analysis: {e}")
            raise DatabaseError(f"Database error creating analysis: {e}")
    
    @staticmethod
    def get_analysis_by_lead(lead_id: int) -> Optional[WebsiteAnalysis]:
        """Get analysis for a lead.
        
        Args:
            lead_id: Lead ID
            
        Returns:
            WebsiteAnalysis object or None
        """
        try:
            with get_database_connection() as conn:
                cursor = conn.execute("""
                    SELECT * FROM website_analysis 
                    WHERE lead_id = ?
                    ORDER BY analyzed_at DESC
                    LIMIT 1
                """, (lead_id,))
                row = cursor.fetchone()
                
                if row:
                    return WebsiteAnalysis.from_dict(dict(row))
                return None
                
        except sqlite3.Error as e:
            logger.error(f"Failed to get analysis for lead {lead_id}: {e}")
            raise DatabaseError(f"Database error getting analysis: {e}")
    
    @staticmethod
    def get_analysis_statistics() -> Dict[str, Any]:
        """Get analysis statistics."""
        try:
            with get_database_connection() as conn:
                # Total analyses
                cursor = conn.execute("SELECT COUNT(*) FROM website_analysis")
                total_analyses = cursor.fetchone()[0]
                
                # Average scores
                cursor = conn.execute("""
                    SELECT 
                        AVG(lighthouse_score) as avg_lighthouse,
                        AVG(performance_score) as avg_performance,
                        AVG(seo_score) as avg_seo,
                        AVG(accessibility_score) as avg_accessibility,
                        AVG(best_practices_score) as avg_best_practices
                    FROM website_analysis
                    WHERE lighthouse_score IS NOT NULL
                """)
                row = cursor.fetchone()
                
                # Recent analyses
                week_ago = (datetime.now() - timedelta(days=7)).isoformat()
                cursor = conn.execute("""
                    SELECT COUNT(*) FROM website_analysis 
                    WHERE analyzed_at > ?
                """, (week_ago,))
                recent_analyses = cursor.fetchone()[0]
                
                return {
                    'total_analyses': total_analyses,
                    'recent_analyses_7d': recent_analyses,
                    'avg_lighthouse_score': round(row[0] or 0, 1),
                    'avg_performance_score': round(row[1] or 0, 1),
                    'avg_seo_score': round(row[2] or 0, 1),
                    'avg_accessibility_score': round(row[3] or 0, 1),
                    'avg_best_practices_score': round(row[4] or 0, 1)
                }
                
        except sqlite3.Error as e:
            logger.error(f"Failed to get analysis statistics: {e}")
            raise DatabaseError(f"Database error getting analysis statistics: {e}")

    @staticmethod
    def get_recent_analyses(limit: Optional[int] = None, offset: int = 0) -> List[WebsiteAnalysis]:
        """Get recent website analyses.
        
        Args:
            limit: Maximum results to return
            offset: Number of results to skip
            
        Returns:
            List of WebsiteAnalysis objects
        """
        limit_sql = f"LIMIT {limit}" if limit else ""
        offset_sql = f"OFFSET {offset}" if offset > 0 else ""
        
        try:
            with get_database_connection() as conn:
                cursor = conn.execute(f"""
                    SELECT wa.*, l.name as lead_name
                    FROM website_analysis wa
                    LEFT JOIN leads l ON wa.lead_id = l.id
                    ORDER BY wa.analyzed_at DESC
                    {limit_sql}
                    {offset_sql}
                """)
                
                rows = cursor.fetchall()
                analyses = []
                for row in rows:
                    analysis_data = dict(row)
                    analysis = WebsiteAnalysis.from_dict(analysis_data)
                    analysis.lead_name = analysis_data.get('lead_name')
                    analyses.append(analysis)
                
                return analyses
                
        except sqlite3.Error as e:
            logger.error(f"Failed to get recent analyses: {e}")
            raise DatabaseError(f"Database error getting recent analyses: {e}")


class EmailOperations:
    """Database operations for email campaigns."""
    
    @staticmethod
    def create_email_campaign(campaign_data: Dict[str, Any]) -> int:
        """Create email campaign record.
        
        Args:
            campaign_data: Email campaign data
            
        Returns:
            ID of created campaign
        """
        campaign = EmailCampaign(
            lead_id=campaign_data['lead_id'],
            subject=campaign_data['subject'],
            email_content=campaign_data['email_content'],
            email_html=campaign_data.get('email_html'),
            template_used=campaign_data.get('template_used'),
            personalization_data=campaign_data.get('personalization_data')
        )
        
        try:
            with get_database_connection() as conn:
                cursor = conn.execute("""
                    INSERT INTO email_campaigns
                    (lead_id, subject, email_content, email_html,
                     template_used, personalization_data, status)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    campaign.lead_id, campaign.subject, campaign.email_content,
                    campaign.email_html, campaign.template_used,
                    campaign.personalization_data, campaign.status
                ))
                
                campaign_id = cursor.lastrowid
                logger.info(f"Created email campaign {campaign_id} for lead {campaign.lead_id}")
                return campaign_id
                
        except sqlite3.Error as e:
            logger.error(f"Failed to create email campaign: {e}")
            raise DatabaseError(f"Database error creating email campaign: {e}")
    
    @staticmethod
    def update_email_status(
        campaign_id: int, 
        status: str, 
        sent_at: Optional[datetime] = None,
        bounce_reason: Optional[str] = None
    ) -> bool:
        """Update email campaign status.
        
        Args:
            campaign_id: Campaign ID
            status: New status
            sent_at: When email was sent
            bounce_reason: Reason for bounce if applicable
            
        Returns:
            True if updated successfully
        """
        updates = {'status': status}
        
        if sent_at:
            updates['sent_at'] = sent_at.isoformat()
        
        if bounce_reason:
            updates['bounce_reason'] = bounce_reason
        
        try:
            with get_database_connection() as conn:
                # Build update query
                set_clauses = [f"{field} = ?" for field in updates.keys()]
                values = list(updates.values()) + [campaign_id]
                
                cursor = conn.execute(f"""
                    UPDATE email_campaigns 
                    SET {', '.join(set_clauses)}
                    WHERE id = ?
                """, values)
                
                # Update lead status if email was sent
                if status == EmailStatus.SENT.value:
                    # Get lead_id for this campaign
                    cursor = conn.execute(
                        "SELECT lead_id FROM email_campaigns WHERE id = ?",
                        (campaign_id,)
                    )
                    row = cursor.fetchone()
                    if row:
                        LeadOperations.update_lead_status(
                            row[0], LeadStatus.EMAIL_SENT.value
                        )
                
                updated = cursor.rowcount > 0
                if updated:
                    logger.debug(f"Updated email campaign {campaign_id} status to {status}")
                return updated
                
        except sqlite3.Error as e:
            logger.error(f"Failed to update email campaign {campaign_id}: {e}")
            raise DatabaseError(f"Database error updating email campaign: {e}")
    
    @staticmethod
    def get_pending_emails(limit: Optional[int] = None) -> List[EmailCampaign]:
        """Get pending email campaigns.
        
        Args:
            limit: Maximum results to return
            
        Returns:
            List of EmailCampaign objects
        """
        limit_sql = f"LIMIT {limit}" if limit else ""
        
        try:
            with get_database_connection() as conn:
                cursor = conn.execute(f"""
                    SELECT * FROM email_campaigns 
                    WHERE status = ?
                    ORDER BY created_at ASC
                    {limit_sql}
                """, (EmailStatus.PENDING.value,))
                
                rows = cursor.fetchall()
                return [EmailCampaign.from_dict(dict(row)) for row in rows]
                
        except sqlite3.Error as e:
            logger.error(f"Failed to get pending emails: {e}")
            raise DatabaseError(f"Database error getting pending emails: {e}")
    
    @staticmethod
    def get_daily_email_count(date: Optional[datetime] = None) -> int:
        """Get number of emails sent on a specific date.
        
        Args:
            date: Date to check (defaults to today)
            
        Returns:
            Number of emails sent
        """
        if date is None:
            date = datetime.now()
        
        start_of_day = date.replace(hour=0, minute=0, second=0, microsecond=0)
        end_of_day = date.replace(hour=23, minute=59, second=59, microsecond=999999)
        
        try:
            with get_database_connection() as conn:
                cursor = conn.execute("""
                    SELECT COUNT(*) FROM email_campaigns 
                    WHERE status = ? AND sent_at BETWEEN ? AND ?
                """, (
                    EmailStatus.SENT.value,
                    start_of_day.isoformat(),
                    end_of_day.isoformat()
                ))
                
                return cursor.fetchone()[0]
                
        except sqlite3.Error as e:
            logger.error(f"Failed to get daily email count: {e}")
            raise DatabaseError(f"Database error getting daily email count: {e}")
    
    @staticmethod
    def get_email_statistics() -> Dict[str, Any]:
        """Get email campaign statistics."""
        try:
            with get_database_connection() as conn:
                # Total counts by status
                cursor = conn.execute("""
                    SELECT status, COUNT(*) as count 
                    FROM email_campaigns 
                    GROUP BY status
                """)
                status_counts = dict(cursor.fetchall())
                
                # Daily send count
                today_count = EmailOperations.get_daily_email_count()
                
                # Recent activity (last 7 days)
                week_ago = (datetime.now() - timedelta(days=7)).isoformat()
                cursor = conn.execute("""
                    SELECT COUNT(*) FROM email_campaigns 
                    WHERE created_at > ?
                """, (week_ago,))
                recent_campaigns = cursor.fetchone()[0]
                
                # Success rate
                cursor = conn.execute("""
                    SELECT 
                        COUNT(*) as total_sent,
                        SUM(CASE WHEN status = 'sent' THEN 1 ELSE 0 END) as successful,
                        SUM(CASE WHEN status = 'bounced' THEN 1 ELSE 0 END) as bounced
                    FROM email_campaigns
                    WHERE status IN ('sent', 'bounced', 'delivered')
                """)
                row = cursor.fetchone()
                
                success_rate = 0
                if row[0] > 0:
                    success_rate = round((row[1] / row[0]) * 100, 1)
                
                return {
                    'total_campaigns': sum(status_counts.values()),
                    'emails_sent_today': today_count,
                    'recent_campaigns_7d': recent_campaigns,
                    'success_rate_percent': success_rate,
                    'status_breakdown': status_counts
                }
                
        except sqlite3.Error as e:
            logger.error(f"Failed to get email statistics: {e}")
            raise DatabaseError(f"Database error getting email statistics: {e}")

    @staticmethod
    def get_recent_emails(limit: Optional[int] = None, offset: int = 0) -> List[EmailCampaign]:
        """Get recent email campaigns.
        
        Args:
            limit: Maximum results to return
            offset: Number of results to skip
            
        Returns:
            List of EmailCampaign objects
        """
        limit_sql = f"LIMIT {limit}" if limit else ""
        offset_sql = f"OFFSET {offset}" if offset > 0 else ""
        
        try:
            with get_database_connection() as conn:
                cursor = conn.execute(f"""
                    SELECT ec.*, l.name as lead_name
                    FROM email_campaigns ec
                    LEFT JOIN leads l ON ec.lead_id = l.id
                    ORDER BY ec.created_at DESC
                    {limit_sql}
                    {offset_sql}
                """)
                
                rows = cursor.fetchall()
                campaigns = []
                for row in rows:
                    campaign_data = dict(row)
                    campaign = EmailCampaign.from_dict(campaign_data)
                    campaign.lead_name = campaign_data.get('lead_name')
                    campaigns.append(campaign)
                
                return campaigns
                
        except sqlite3.Error as e:
            logger.error(f"Failed to get recent emails: {e}")
            raise DatabaseError(f"Database error getting recent emails: {e}")

    @staticmethod
    def get_email_campaign(campaign_id: int) -> Optional[EmailCampaign]:
        """Get email campaign by ID.
        
        Args:
            campaign_id: Campaign ID
            
        Returns:
            EmailCampaign object or None if not found
        """
        try:
            with get_database_connection() as conn:
                cursor = conn.execute("""
                    SELECT ec.*, l.name as lead_name
                    FROM email_campaigns ec
                    LEFT JOIN leads l ON ec.lead_id = l.id
                    WHERE ec.id = ?
                """, (campaign_id,))
                
                row = cursor.fetchone()
                if row:
                    campaign_data = dict(row)
                    campaign = EmailCampaign.from_dict(campaign_data)
                    campaign.lead_name = campaign_data.get('lead_name')
                    return campaign
                return None
                
        except sqlite3.Error as e:
            logger.error(f"Failed to get email campaign {campaign_id}: {e}")
            raise DatabaseError(f"Database error getting email campaign: {e}")


@contextmanager
def database_transaction():
    """Context manager for database transactions."""
    db = next(get_db())
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def initialize_database():
    """Initialize database and create tables."""
    try:
        init_db()
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        raise DatabaseError(f"Database initialization failed: {e}")


def get_dashboard_data() -> Dict[str, Any]:
    """Get comprehensive data for dashboard.
    
    Returns:
        Dictionary with all dashboard statistics
    """
    try:
        return {
            'leads': LeadOperations.get_lead_statistics(),
            'analysis': AnalysisOperations.get_analysis_statistics(),
            'emails': EmailOperations.get_email_statistics(),
            'timestamp': datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Failed to get dashboard data: {e}")
        raise DatabaseError(f"Error getting dashboard data: {e}")


# Convenience functions for common operations
def add_lead(name: str, **kwargs) -> int:
    """Add a new lead with minimal data."""
    lead_data = {'name': name, **kwargs}
    return LeadOperations.create_lead(lead_data)


def find_leads_needing_analysis() -> List[Lead]:
    """Find leads that need website analysis."""
    return LeadOperations.get_leads_for_analysis()


def find_leads_ready_for_email() -> List[Lead]:
    """Find leads ready for email outreach.""" 
    return LeadOperations.get_leads_for_email()


def can_send_more_emails_today() -> bool:
    """Check if we can send more emails today."""
    settings = get_settings()
    today_count = EmailOperations.get_daily_email_count()
    return today_count < settings.emails_per_day_limit 
"""CLI commands for PitchPerfect AI."""

import click
from typing import Optional, List
from datetime import datetime, timedelta
import json
import sys

from ..config import get_settings
from ..utils import get_logger
from ..database.operations import LeadOperations, EmailOperations, AnalysisOperations
from ..scraper import ScrapingOrchestrator
from ..analyzer import LLMAnalyzer
from ..email_system import EmailSender
from ..dashboard import Dashboard


@click.group()
def cli():
    """PitchPerfect AI - Automated Lead Generation and Outreach System."""
    pass


@cli.command()
def status():
    """Show system status and configuration."""
    settings = get_settings()
    logger = get_logger()
    
    click.echo("=== PitchPerfect AI System Status ===")
    click.echo()
    
    # Configuration status
    click.echo("Configuration:")
    click.echo(f"  Database: {settings.database_path}")
    click.echo(f"  Gmail SMTP: {'✓ Configured' if settings.gmail_email and settings.gmail_app_password else '✗ Not configured'}")
    click.echo(f"  Ollama LLM: {'✓ Configured' if settings.ollama_base_url else '✗ Not configured'}")
    click.echo(f"  Daily Email Limit: {settings.emails_per_day_limit}")
    click.echo()
    
    # Database status
    try:
        lead_ops = LeadOperations()
        email_ops = EmailOperations()
        analysis_ops = AnalysisOperations()
        
        total_leads = lead_ops.get_lead_statistics().get('total_leads', 0)
        total_emails = email_ops.get_email_statistics().get('total_campaigns', 0)
        total_analyses = analysis_ops.get_analysis_statistics().get('total_analyses', 0)
        
        click.echo("Database Statistics:")
        click.echo(f"  Total Leads: {total_leads}")
        click.echo(f"  Total Emails: {total_emails}")
        click.echo(f"  Total Analyses: {total_analyses}")
        click.echo()
        
    except Exception as e:
        click.echo(f"Database Error: {e}")
        click.echo()
    
    # Email system status
    try:
        email_sender = EmailSender()
        email_test = email_sender.test_email_system()
        
        click.echo("Email System:")
        click.echo(f"  SMTP Connection: {'✓ Working' if email_test['smtp_connection'] else '✗ Failed'}")
        click.echo(f"  Template Engine: {'✓ Working' if email_test['template_engine'] else '✗ Failed'}")
        click.echo(f"  Database Connection: {'✓ Working' if email_test['database_connection'] else '✗ Failed'}")
        click.echo()
        
    except Exception as e:
        click.echo(f"Email System Error: {e}")
        click.echo()
    
    # LLM status
    try:
        llm_analyzer = LLMAnalyzer()
        llm_status = llm_analyzer.test_connection()
        
        click.echo("LLM Analyzer:")
        click.echo(f"  Connection: {'✓ Working' if llm_status else '✗ Failed'}")
        click.echo()
        
    except Exception as e:
        click.echo(f"LLM Error: {e}")
        click.echo()


@cli.command()
def init_db():
    """Initialize database tables."""
    from ..database import initialize_database
    
    click.echo("Initializing database...")
    try:
        initialize_database()
        click.echo("✓ Database initialized successfully")
    except Exception as e:
        click.echo(f"✗ Database initialization failed: {e}")


@cli.command()
@click.option('--source', type=click.Choice(['google_maps']), default='google_maps', help='Source to scrape')
@click.option('--max-leads', default=50, help='Maximum number of leads to scrape')
@click.option('--save-to-db', is_flag=True, default=True, help='Save results to database')
def scrape_leads(search_term: str, source: str, max_leads: int, save_to_db: bool):
    """Scrape leads from various sources."""
    try:
        from src.scraper.orchestrator import ScraperOrchestrator
        
        orchestrator = ScraperOrchestrator()
        
        sources = [source]
        
        click.echo(f"Starting lead scraping for: {search_term}")
        click.echo(f"Sources: {sources}")
        click.echo(f"Max leads: {max_leads}")
        click.echo(f"Save to DB: {save_to_db}")
        click.echo("-" * 50)
        
        results = orchestrator.scrape_leads(
            search_term=search_term,
            max_results=max_leads,
            sources=sources,
            save_to_db=save_to_db
        )
        
        # Display results
        total_leads = 0
        for source_name, result in results.items():
            click.echo(f"\n{source_name.upper()} Results:")
            click.echo(f"  Status: {'✅ Success' if result.success else '❌ Failed'}")
            click.echo(f"  Leads found: {len(result.leads)}")
            click.echo(f"  Errors: {len(result.errors)}")
            
            if result.errors:
                for error in result.errors:
                    click.echo(f"    - {error}")
            
            if result.leads:
                click.echo("  Sample leads:")
                for i, lead in enumerate(result.leads[:3]):  # Show first 3
                    click.echo(f"    {i+1}. {lead.get('name', 'Unknown')}")
                    click.echo(f"       Phone: {lead.get('phone', 'N/A')}")
                    click.echo(f"       Website: {lead.get('website', 'N/A')}")
                    click.echo(f"       Email: {lead.get('email', 'N/A')}")
                    click.echo()
            
            total_leads += len(result.leads)
        
        click.echo(f"\n{'='*50}")
        click.echo(f"Total leads scraped: {total_leads}")
        click.echo("Scraping completed!")
        
    except Exception as e:
        click.echo(f"Error during scraping: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.option('--lead-id', type=int, help='Analyze specific lead by ID')
@click.option('--all', is_flag=True, help='Analyze all leads without analysis')
@click.option('--limit', type=int, default=10, help='Maximum number of leads to analyze')
def analyze(lead_id, all, limit):
    """Analyze website performance and SEO for leads."""
    if lead_id:
        click.echo(f"Analyzing lead {lead_id}...")
        try:
            lead_ops = LeadOperations()
            analysis_ops = AnalysisOperations()
            llm_analyzer = LLMAnalyzer()
            
            lead = lead_ops.get_lead_by_id(lead_id)
            if not lead:
                click.echo(f"✗ Lead {lead_id} not found")
                return
            
            analysis = llm_analyzer.analyze_website(lead)
            if analysis:
                click.echo(f"✓ Analysis completed for {lead.name}")
                click.echo(f"  SEO Score: {analysis.seo_score}")
                click.echo(f"  Performance Score: {analysis.performance_score}")
            else:
                click.echo(f"✗ Analysis failed for {lead.name}")
                
        except Exception as e:
            click.echo(f"✗ Analysis failed: {e}")
    
    elif all:
        click.echo("Analyzing all leads without analysis...")
        try:
            lead_ops = LeadOperations()
            analysis_ops = AnalysisOperations()
            llm_analyzer = LLMAnalyzer()
            
            from ..database.operations import find_leads_needing_analysis
            leads = find_leads_needing_analysis()
            if not leads:
                click.echo("No leads found without analysis")
                return
            
            click.echo(f"Found {len(leads)} leads to analyze")
            
            for i, lead in enumerate(leads[:limit], 1):
                click.echo(f"Analyzing {lead.name} ({i}/{min(len(leads), limit)})...")
                
                try:
                    analysis = llm_analyzer.analyze_website(lead)
                    if analysis:
                        click.echo(f"  ✓ {lead.name}: SEO {analysis.seo_score}, Performance {analysis.performance_score}")
                    else:
                        click.echo(f"  ✗ {lead.name}: Analysis failed")
                except Exception as e:
                    click.echo(f"  ✗ {lead.name}: {e}")
            
            click.echo(f"✓ Analysis completed for {min(len(leads), limit)} leads")
            
        except Exception as e:
            click.echo(f"✗ Analysis failed: {e}")
    
    else:
        click.echo("Please specify --lead-id or --all")


@cli.command()
@click.option('--lead-id', type=int, help='Send email to specific lead by ID')
@click.option('--template', type=click.Choice(['website_improvement', 'seo_optimization', 'performance_boost', 'general_outreach']), default='website_improvement', help='Email template to use')
@click.option('--all-analyzed', is_flag=True, help='Send emails to all analyzed leads')
@click.option('--limit', type=int, default=10, help='Maximum number of emails to send')
@click.option('--preview', is_flag=True, help='Preview email without sending')
def send_email(lead_id, template, all_analyzed, limit, preview):
    """Send cold emails to leads."""
    try:
        email_sender = EmailSender()
        lead_ops = LeadOperations()
        analysis_ops = AnalysisOperations()
        
        if lead_id:
            click.echo(f"Sending email to lead {lead_id}...")
            
            lead = lead_ops.get_lead_by_id(lead_id)
            if not lead:
                click.echo(f"✗ Lead {lead_id} not found")
                return
            
            analysis = analysis_ops.get_analysis_by_lead_id(lead_id)
            
            if preview:
                email_data = email_sender.preview_email(lead, template, analysis)
                click.echo("=== Email Preview ===")
                click.echo(f"To: {lead.email}")
                click.echo(f"Subject: {email_data['subject']}")
                click.echo(f"Body:\n{email_data['body']}")
                return
            
            result = email_sender.send_single_email(lead, template, analysis)
            
            if result['success']:
                click.echo(f"✓ Email sent to {lead.name}")
            else:
                click.echo(f"✗ Failed to send email to {lead.name}")
        
        elif all_analyzed:
            click.echo("Sending emails to all analyzed leads...")
            
            from ..database.operations import find_leads_ready_for_email
            leads = find_leads_ready_for_email()
            if not leads:
                click.echo("No leads found ready for emailing")
                return
            
            click.echo(f"Found {len(leads)} leads ready for emailing")
            
            # Get analyses for all leads
            analyses = {}
            for lead in leads:
                analysis = analysis_ops.get_analysis_by_lead_id(lead.id)
                if analysis:
                    analyses[lead.id] = analysis
            
            if preview:
                click.echo("=== Email Preview (First Lead) ===")
                if leads:
                    lead = leads[0]
                    analysis = analyses.get(lead.id)
                    email_data = email_sender.preview_email(lead, template, analysis)
                    click.echo(f"To: {lead.email}")
                    click.echo(f"Subject: {email_data['subject']}")
                    click.echo(f"Body:\n{email_data['body']}")
                return
            
            results = email_sender.send_analysis_based_emails(
                leads[:limit],
                analyses,
                delay_between=2.0
            )
            
            click.echo(f"✓ Sent {results['emails_sent']} emails")
            click.echo(f"✗ Failed to send {results['emails_failed']} emails")
            
            if results['template_usage']:
                click.echo("Template usage:")
                for template_type, count in results['template_usage'].items():
                    if count > 0:
                        click.echo(f"  {template_type}: {count}")
        
        else:
            click.echo("Please specify --lead-id or --all-analyzed")
            
    except Exception as e:
        click.echo(f"✗ Email sending failed: {e}")


@cli.command()
def dashboard():
    """Show system dashboard."""
    try:
        dashboard = Dashboard()
        
        click.echo("=== PitchPerfect AI Dashboard ===")
        click.echo()
        
        # System overview
        overview = dashboard.get_system_overview()
        if 'error' not in overview:
            db_stats = overview['database']
            click.echo("System Overview:")
            click.echo(f"  Total Leads: {db_stats['total_leads']}")
            click.echo(f"  Total Emails: {db_stats['total_emails']}")
            click.echo(f"  Total Analyses: {db_stats['total_analyses']}")
            click.echo(f"  Recent Activity (7 days): {db_stats['recent_leads']} leads, {db_stats['recent_emails']} emails")
            click.echo()
        
        # Pipeline progress
        progress = dashboard.get_pipeline_progress()
        if 'error' not in progress:
            click.echo("Pipeline Progress:")
            click.echo(f"  Leads without analysis: {progress['leads_without_analysis']}")
            click.echo(f"  Analyses without emails: {progress['analyses_without_emails']}")
            click.echo(f"  Leads ready for email: {progress['leads_ready_for_email']}")
            click.echo()
        
        # Email statistics
        email_stats = dashboard.get_email_statistics()
        if 'error' not in email_stats:
            db_stats = email_stats['database']
            smtp_stats = email_stats['smtp']
            click.echo("Email Statistics:")
            click.echo(f"  Total Emails: {db_stats['total_emails']}")
            click.echo(f"  Sent: {db_stats['sent_emails']}")
            click.echo(f"  Failed: {db_stats['failed_emails']}")
            click.echo(f"  Success Rate: {db_stats['success_rate']:.1f}%")
            click.echo(f"  Sent Today: {smtp_stats['emails_sent_today']}/{smtp_stats['daily_limit']}")
            click.echo()
        
        # Recommendations
        recommendations = dashboard.get_recommendations()
        if recommendations:
            click.echo("Recommendations:")
            for rec in recommendations:
                priority_icon = "🔴" if rec['priority'] == 'high' else "🟡" if rec['priority'] == 'medium' else "🟢"
                click.echo(f"  {priority_icon} {rec['message']}")
            click.echo()
        
    except Exception as e:
        click.echo(f"✗ Dashboard error: {e}")


@cli.command()
@click.option('--format', type=click.Choice(['json', 'csv']), default='json', help='Export format')
@click.option('--output', help='Output file path')
def export_data(format, output):
    """Export system data."""
    try:
        dashboard = Dashboard()
        data = dashboard.export_dashboard_data(format)
        
        if output:
            with open(output, 'w') as f:
                f.write(data)
            click.echo(f"✓ Data exported to {output}")
        else:
            click.echo(data)
            
    except Exception as e:
        click.echo(f"✗ Export failed: {e}")


@cli.command()
def test_system():
    """Test all system components."""
    click.echo("Testing PitchPerfect AI system...")
    click.echo()
    
    # Test database
    click.echo("Testing database...")
    try:
        lead_ops = LeadOperations()
        lead_count = lead_ops.get_lead_count()
        click.echo(f"  ✓ Database working ({lead_count} leads)")
    except Exception as e:
        click.echo(f"  ✗ Database error: {e}")
    
    # Test email system
    click.echo("Testing email system...")
    try:
        email_sender = EmailSender()
        email_test = email_sender.test_email_system()
        
        if email_test['overall_status']:
            click.echo("  ✓ Email system working")
        else:
            click.echo("  ✗ Email system issues detected")
            for component, status in email_test.items():
                if component != 'overall_status':
                    status_icon = "✓" if status else "✗"
                    click.echo(f"    {status_icon} {component}")
    except Exception as e:
        click.echo(f"  ✗ Email system error: {e}")
    
    # Test LLM analyzer
    click.echo("Testing LLM analyzer...")
    try:
        llm_analyzer = LLMAnalyzer()
        llm_status = llm_analyzer.test_connection()
        
        if llm_status:
            click.echo("  ✓ LLM analyzer working")
        else:
            click.echo("  ✗ LLM analyzer not responding")
    except Exception as e:
        click.echo(f"  ✗ LLM analyzer error: {e}")
    
    # Test scrapers
    click.echo("Testing scrapers...")
    try:
        orchestrator = ScrapingOrchestrator()
        click.echo("  ✓ Scraping orchestrator initialized")
    except Exception as e:
        click.echo(f"  ✗ Scraper error: {e}")
    
    click.echo()
    click.echo("System test completed")


@cli.command()
@click.option('--days', type=int, default=7, help='Number of days to look back')
def recent_activity(days):
    """Show recent system activity."""
    try:
        lead_ops = LeadOperations()
        email_ops = EmailOperations()
        analysis_ops = AnalysisOperations()
        
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        recent_leads = lead_ops.get_leads_by_date_range(start_date, end_date)
        recent_emails = email_ops.get_emails_by_date_range(start_date, end_date)
        recent_analyses = analysis_ops.get_analyses_by_date_range(start_date, end_date)
        
        click.echo(f"=== Recent Activity (Last {days} days) ===")
        click.echo()
        
        click.echo(f"New Leads: {len(recent_leads)}")
        for lead in recent_leads[:5]:  # Show first 5
            click.echo(f"  - {lead.name} ({lead.source})")
        if len(recent_leads) > 5:
            click.echo(f"  ... and {len(recent_leads) - 5} more")
        click.echo()
        
        click.echo(f"Emails Sent: {len(recent_emails)}")
        for email in recent_emails[:5]:  # Show first 5
            lead = lead_ops.get_lead_by_id(email.lead_id)
            lead_name = lead.name if lead else f"Lead {email.lead_id}"
            click.echo(f"  - {lead_name} ({email.template_type})")
        if len(recent_emails) > 5:
            click.echo(f"  ... and {len(recent_emails) - 5} more")
        click.echo()
        
        click.echo(f"Analyses Completed: {len(recent_analyses)}")
        for analysis in recent_analyses[:5]:  # Show first 5
            lead = lead_ops.get_lead_by_id(analysis.lead_id)
            lead_name = lead.name if lead else f"Lead {analysis.lead_id}"
            click.echo(f"  - {lead_name} (SEO: {analysis.seo_score}, Performance: {analysis.performance_score})")
        if len(recent_analyses) > 5:
            click.echo(f"  ... and {len(recent_analyses) - 5} more")
        
    except Exception as e:
        click.echo(f"✗ Error getting recent activity: {e}")


if __name__ == '__main__':
    cli() 
"""Gmail SMTP client for PitchPerfect AI."""

import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
import time

from ..config import get_settings
from ..utils import get_logger, LoggerMixin, validate_email, get_rate_limiter
from ..database.operations import EmailOperations, EmailStatus


class SMTPError(Exception):
    """Custom SMTP error."""
    pass


class SMTPClient(LoggerMixin):
    """Gmail SMTP client for sending cold emails."""
    
    def __init__(self):
        """Initialize SMTP client."""
        self.settings = get_settings()
        self.rate_limiter = get_rate_limiter("email")
        self.daily_sent = 0
        self.last_reset = datetime.now().date()
        
        # Validate SMTP settings
        if not self.settings.gmail_email or not self.settings.gmail_app_password:
            raise SMTPError("Gmail email and app password must be configured")
        
        self.logger.info("SMTP client initialized")
    
    def _reset_daily_counter(self):
        """Reset daily email counter if it's a new day."""
        today = datetime.now().date()
        if today > self.last_reset:
            self.daily_sent = 0
            self.last_reset = today
            self.logger.info("Daily email counter reset")
    
    def _check_daily_limit(self) -> bool:
        """Check if we can send more emails today.
        
        Returns:
            True if we can send more emails
        """
        self._reset_daily_counter()
        return self.daily_sent < self.settings.emails_per_day_limit
    
    def _create_message(
        self,
        to_email: str,
        subject: str,
        body: str,
        from_name: Optional[str] = None
    ) -> MIMEMultipart:
        """Create email message.
        
        Args:
            to_email: Recipient email
            subject: Email subject
            body: Email body
            from_name: Sender name
            
        Returns:
            MIME message object
        """
        message = MIMEMultipart("alternative")
        message["Subject"] = subject
        message["From"] = f"{from_name or 'PitchPerfect AI'} <{self.settings.gmail_email}>"
        message["To"] = to_email
        
        # Add text and HTML parts
        text_part = MIMEText(body, "plain")
        message.attach(text_part)
        
        # Add HTML version if body contains HTML
        if "<html>" in body.lower():
            html_part = MIMEText(body, "html")
            message.attach(html_part)
        
        return message
    
    def _send_message(self, message: MIMEMultipart) -> bool:
        """Send email message via Gmail SMTP.
        
        Args:
            message: MIME message to send
            
        Returns:
            True if sent successfully
        """
        try:
            # Apply rate limiting
            self.rate_limiter.wait_if_needed()
            
            # Create SSL context
            context = ssl.create_default_context()
            
            # Connect to Gmail SMTP
            with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=context) as server:
                # Login
                server.login(self.settings.gmail_email, self.settings.gmail_app_password)
                
                # Send email
                server.send_message(message)
                
                self.rate_limiter.record_request(success=True)
                self.daily_sent += 1
                
                self.logger.info(f"Email sent successfully to {message['To']}")
                return True
                
        except smtplib.SMTPAuthenticationError as e:
            self.rate_limiter.record_request(success=False)
            error_msg = f"SMTP authentication failed: {e}"
            self.logger.error(error_msg)
            raise SMTPError(error_msg)
            
        except smtplib.SMTPRecipientsRefused as e:
            self.rate_limiter.record_request(success=False)
            error_msg = f"Recipient refused: {e}"
            self.logger.warning(error_msg)
            return False
            
        except smtplib.SMTPServerDisconnected as e:
            self.rate_limiter.record_request(success=False)
            error_msg = f"SMTP server disconnected: {e}"
            self.logger.error(error_msg)
            raise SMTPError(error_msg)
            
        except Exception as e:
            self.rate_limiter.record_request(success=False)
            error_msg = f"SMTP error: {e}"
            self.logger.error(error_msg)
            raise SMTPError(error_msg)
    
    def send_email(
        self,
        to_email: str,
        subject: str,
        body: str,
        from_name: Optional[str] = None
    ) -> bool:
        """Send a single email.
        
        Args:
            to_email: Recipient email address
            subject: Email subject line
            body: Email body content
            from_name: Sender name (optional)
            
        Returns:
            True if sent successfully
        """
        # Validate email
        email_validation = validate_email(to_email)
        if not email_validation.is_valid:
            self.logger.warning(f"Invalid email address: {to_email}")
            return False
        
        # Check daily limit
        if not self._check_daily_limit():
            self.logger.warning(f"Daily email limit reached ({self.settings.emails_per_day_limit})")
            return False
        
        # Create and send message
        try:
            message = self._create_message(to_email, subject, body, from_name)
            return self._send_message(message)
            
        except Exception as e:
            self.logger.error(f"Failed to send email to {to_email}: {e}")
            return False
    
    def send_bulk_emails(
        self,
        emails: List[Dict[str, Any]],
        delay_between: float = 2.0
    ) -> Dict[str, Any]:
        """Send multiple emails with rate limiting.
        
        Args:
            emails: List of email dictionaries with keys: to_email, subject, body, from_name
            delay_between: Delay between emails in seconds
            
        Returns:
            Dictionary with results summary
        """
        results = {
            'total': len(emails),
            'sent': 0,
            'failed': 0,
            'skipped': 0,
            'errors': []
        }
        
        self.logger.info(f"Starting bulk email send: {len(emails)} emails")
        
        for i, email_data in enumerate(emails):
            try:
                # Check daily limit
                if not self._check_daily_limit():
                    self.logger.warning("Daily limit reached, stopping bulk send")
                    results['skipped'] = len(emails) - i
                    break
                
                # Send email
                success = self.send_email(
                    to_email=email_data['to_email'],
                    subject=email_data['subject'],
                    body=email_data['body'],
                    from_name=email_data.get('from_name')
                )
                
                if success:
                    results['sent'] += 1
                else:
                    results['failed'] += 1
                
                # Progress logging
                if (i + 1) % 10 == 0:
                    self.logger.info(f"Progress: {i + 1}/{len(emails)} emails processed")
                
                # Delay between emails
                if i < len(emails) - 1:  # Don't delay after last email
                    time.sleep(delay_between)
                    
            except Exception as e:
                results['failed'] += 1
                results['errors'].append(f"Email {i + 1}: {str(e)}")
                self.logger.error(f"Error sending email {i + 1}: {e}")
        
        self.logger.info(f"Bulk email completed: {results['sent']} sent, {results['failed']} failed")
        return results
    
    def test_connection(self) -> bool:
        """Test SMTP connection and authentication.
        
        Returns:
            True if connection successful
        """
        try:
            context = ssl.create_default_context()
            
            with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=context) as server:
                server.login(self.settings.gmail_email, self.settings.gmail_app_password)
                
            self.logger.info("SMTP connection test successful")
            return True
            
        except Exception as e:
            self.logger.error(f"SMTP connection test failed: {e}")
            return False
    
    def get_daily_stats(self) -> Dict[str, Any]:
        """Get daily email statistics.
        
        Returns:
            Dictionary with daily stats
        """
        self._reset_daily_counter()
        
        return {
            'emails_sent_today': self.daily_sent,
            'daily_limit': self.settings.emails_per_day_limit,
            'remaining_today': max(0, self.settings.emails_per_day_limit - self.daily_sent),
            'last_reset': self.last_reset.isoformat()
        }
    
    def get_rate_limit_info(self) -> Dict[str, Any]:
        """Get rate limiting information.
        
        Returns:
            Dictionary with rate limit stats
        """
        return {
            'daily_sent': self.daily_sent,
            'daily_limit': self.settings.emails_per_day_limit,
            'rate_limiter_stats': self.rate_limiter.get_stats()
        } 
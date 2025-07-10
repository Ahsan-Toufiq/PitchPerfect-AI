"""Email system package for PitchPerfect AI."""

from .smtp_client import SMTPClient, SMTPError
from .template_engine import EmailTemplateEngine, TemplateError
from .sender import EmailSender, EmailSenderError

__all__ = [
    'SMTPClient',
    'SMTPError', 
    'EmailTemplateEngine',
    'TemplateError',
    'EmailSender',
    'EmailSenderError'
] 
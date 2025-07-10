"""Logging utility for PitchPerfect AI using loguru."""

import sys
from pathlib import Path
from typing import Optional
from loguru import logger

from ..config import get_settings


def setup_logging(
    log_file: Optional[str] = None,
    log_level: Optional[str] = None,
    console_output: bool = True
) -> None:
    """Setup logging configuration with file rotation and console output.
    
    Args:
        log_file: Path to log file (defaults to settings)
        log_level: Log level (defaults to settings) 
        console_output: Whether to output to console
    """
    settings = get_settings()
    
    # Remove default logger
    logger.remove()
    
    log_level = log_level or settings.log_level
    log_file = log_file or settings.log_file
    
    # Ensure log directory exists
    log_path = Path(log_file)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Console logging with colors
    if console_output:
        logger.add(
            sys.stdout,
            level=log_level,
            format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
                   "<level>{level: <8}</level> | "
                   "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
                   "<level>{message}</level>",
            colorize=True
        )
    
    # File logging with rotation
    logger.add(
        log_file,
        level=log_level,
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} | {message}",
        rotation=settings.log_max_size,
        retention=settings.log_backup_count,
        compression="zip",
        enqueue=True,  # Thread-safe
        backtrace=True,
        diagnose=True
    )
    
    logger.info(f"Logging configured - Level: {log_level}, File: {log_file}")


def get_logger(name: str = "pitchperfect"):
    """Get a logger instance with the specified name.
    
    Args:
        name: Logger name (typically __name__)
        
    Returns:
        Configured logger instance
    """
    return logger.bind(name=name)


# Auto-setup logging when module is imported
if not logger._core.handlers:
    setup_logging()


class LoggerMixin:
    """Mixin class to add logging capabilities to any class."""
    
    @property
    def logger(self):
        """Get logger for this class."""
        return get_logger(self.__class__.__name__)
    
    def log_method_call(self, method_name: str, **kwargs):
        """Log method call with parameters."""
        params = ", ".join(f"{k}={v}" for k, v in kwargs.items())
        self.logger.debug(f"Calling {method_name}({params})")
    
    def log_execution_time(self, operation: str, duration: float):
        """Log execution time for an operation."""
        self.logger.info(f"{operation} completed in {duration:.2f}s")
    
    def log_error(self, operation: str, error: Exception):
        """Log error with context."""
        self.logger.error(f"Error in {operation}: {str(error)}", exc_info=True)
    
    def log_success(self, operation: str, details: str = ""):
        """Log successful operation."""
        msg = f"{operation} completed successfully"
        if details:
            msg += f": {details}"
        self.logger.info(msg)


# Convenience functions for common logging patterns
def log_scraping_start(source: str, search_term: str):
    """Log start of scraping operation."""
    logger.info(f"Starting {source} scraping for: '{search_term}'")


def log_scraping_result(source: str, count: int, duration: float):
    """Log scraping results."""
    logger.info(f"{source} scraping completed: {count} leads found in {duration:.2f}s")


def log_analysis_start(website: str):
    """Log start of website analysis."""
    logger.info(f"Starting website analysis for: {website}")


def log_analysis_result(website: str, scores: dict, duration: float):
    """Log analysis results."""
    score_str = ", ".join(f"{k}: {v:.1f}" for k, v in scores.items() if v is not None)
    logger.info(f"Website analysis completed for {website} in {duration:.2f}s - {score_str}")


def log_email_sent(recipient: str, subject: str):
    """Log email sending."""
    logger.info(f"Email sent to {recipient}: '{subject}'")


def log_email_failed(recipient: str, error: str):
    """Log email failure."""
    logger.error(f"Failed to send email to {recipient}: {error}")


def log_rate_limit(operation: str, delay: float):
    """Log rate limiting delay."""
    logger.debug(f"Rate limiting {operation} - waiting {delay:.1f}s")


def log_configuration_issue(component: str, issue: str):
    """Log configuration problems."""
    logger.warning(f"Configuration issue in {component}: {issue}")


def log_external_service_error(service: str, error: str):
    """Log external service errors."""
    logger.error(f"External service error ({service}): {error}") 
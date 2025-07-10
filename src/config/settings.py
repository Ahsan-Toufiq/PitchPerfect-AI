"""Application settings using Pydantic for validation and type safety."""

import os
from pathlib import Path
from typing import Optional
from functools import lru_cache

from pydantic_settings import BaseSettings
from pydantic import validator, EmailStr


class Settings(BaseSettings):
    """Application settings with validation."""
    
    # Application
    app_name: str = "PitchPerfect AI"
    debug: bool = False
    
    # Paths
    project_root: Path = Path(__file__).parent.parent.parent
    data_dir: Path = project_root / "data"
    logs_dir: Path = project_root / "logs"
    
    # Database
    database_path: str = "data/pitchperfect.db"
    
    # Gmail SMTP
    gmail_email: Optional[EmailStr] = None
    gmail_app_password: Optional[str] = None
    
    # Ollama
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3"
    ollama_timeout: int = 120
    
    # Scraping
    scraping_delay_min: int = 2
    scraping_delay_max: int = 5
    max_leads_per_search: int = 50
    chrome_headless: bool = True
    scraping_timeout: int = 30
    user_agent_rotation: bool = True
    
    # Email Settings
    emails_per_day_limit: int = 50
    email_from_name: str = "PitchPerfect AI"
    email_reply_to: Optional[EmailStr] = None
    email_dry_run: bool = False
    
    # Logging
    log_level: str = "INFO"
    log_file: str = "logs/pitchperfect.log"
    log_max_size: int = 10 * 1024 * 1024  # 10MB
    log_backup_count: int = 5
    
    # Dashboard
    dashboard_port: int = 8501
    dashboard_host: str = "localhost"
    dashboard_debug: bool = False
    
    # Rate Limiting
    api_rate_limit_requests: int = 10
    api_rate_limit_period: int = 60
    
    # Website Analysis
    lighthouse_timeout: int = 60
    analysis_concurrent_limit: int = 3
    lighthouse_chrome_flags: str = "--headless --no-sandbox --disable-gpu"
    
    # Security
    max_email_size: int = 1024 * 1024  # 1MB
    allowed_domains: list = []  # Empty = allow all
    blocked_domains: list = ["gmail.com", "yahoo.com", "hotmail.com"]  # No personal emails
    
    class Config:
        """Pydantic config."""
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        
    @validator("database_path")
    def validate_database_path(cls, v, values):
        """Ensure database directory exists."""
        db_path = Path(v)
        db_path.parent.mkdir(parents=True, exist_ok=True)
        return str(db_path)
    
    @validator("log_file")
    def validate_log_file(cls, v, values):
        """Ensure log directory exists."""
        log_path = Path(v)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        return str(log_path)
    
    @validator("data_dir", "logs_dir")
    def validate_directories(cls, v):
        """Ensure required directories exist."""
        Path(v).mkdir(parents=True, exist_ok=True)
        return v
    
    @validator("email_reply_to", pre=True, always=True)
    def validate_email_reply_to(cls, v, values):
        """Default reply-to to gmail_email if not set."""
        if v is None and "gmail_email" in values:
            return values["gmail_email"]
        return v
    
    @validator("log_level")
    def validate_log_level(cls, v):
        """Validate log level."""
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if v.upper() not in valid_levels:
            raise ValueError(f"Log level must be one of: {valid_levels}")
        return v.upper()
    
    @validator("ollama_base_url")
    def validate_ollama_url(cls, v):
        """Validate Ollama URL format."""
        if not v.startswith(("http://", "https://")):
            raise ValueError("Ollama URL must start with http:// or https://")
        return v.rstrip("/")
    
    def get_full_database_path(self) -> Path:
        """Get absolute database path."""
        return self.project_root / self.database_path
    
    def get_full_log_path(self) -> Path:
        """Get absolute log file path."""
        return self.project_root / self.log_file
    
    def is_email_configured(self) -> bool:
        """Check if email is properly configured."""
        return bool(self.gmail_email and self.gmail_app_password)
    
    def is_ollama_configured(self) -> bool:
        """Check if Ollama is configured."""
        return bool(self.ollama_base_url and self.ollama_model)
    
    def get_scraping_delay_range(self) -> tuple[int, int]:
        """Get scraping delay range."""
        return (self.scraping_delay_min, self.scraping_delay_max)
    
    def get_lighthouse_command_args(self) -> list[str]:
        """Get Lighthouse CLI arguments."""
        return [
            "--chrome-flags=" + self.lighthouse_chrome_flags,
            "--output=json",
            "--quiet",
            f"--max-wait-for-load={self.lighthouse_timeout * 1000}",
        ]


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings() 
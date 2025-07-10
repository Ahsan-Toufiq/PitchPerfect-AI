"""Database models and schema for PitchPerfect AI."""

import sqlite3
import json
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, asdict
from enum import Enum

from sqlalchemy import create_engine, Column, Integer, String, DateTime, Text, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os

from ..config import get_settings


class LeadStatus(Enum):
    """Lead status enumeration."""
    NEW = "new"
    ANALYZED = "analyzed"
    EMAIL_SENT = "email_sent"
    REPLIED = "replied"
    BOUNCED = "bounced"
    UNSUBSCRIBED = "unsubscribed"
    FAILED = "failed"


class EmailStatus(Enum):
    """Email status enumeration."""
    PENDING = "pending"
    SENT = "sent"
    DELIVERED = "delivered"
    BOUNCED = "bounced"
    FAILED = "failed"
    UNSUBSCRIBED = "unsubscribed"


@dataclass
class Lead:
    """Lead data model."""
    id: Optional[int] = None
    name: str = ""
    website: Optional[str] = None
    email: Optional[str] = None
    category: Optional[str] = None
    location: Optional[str] = None
    phone: Optional[str] = None
    rating: Optional[float] = None
    review_count: Optional[int] = None
    scraped_at: Optional[datetime] = None
    status: str = LeadStatus.NEW.value
    source: str = "unknown"  # yelp, google_maps, etc.
    metadata: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        data = asdict(self)
        if self.scraped_at:
            data['scraped_at'] = self.scraped_at.isoformat()
        if self.metadata:
            data['metadata'] = json.dumps(self.metadata)
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Lead':
        """Create from dictionary."""
        if 'scraped_at' in data and data['scraped_at']:
            if isinstance(data['scraped_at'], str):
                data['scraped_at'] = datetime.fromisoformat(data['scraped_at'])
        if 'metadata' in data and isinstance(data['metadata'], str):
            data['metadata'] = json.loads(data['metadata'])
        return cls(**data)


@dataclass
class WebsiteAnalysis:
    """Website analysis data model."""
    id: Optional[int] = None
    lead_id: int = 0
    lighthouse_score: Optional[float] = None
    performance_score: Optional[float] = None
    seo_score: Optional[float] = None
    accessibility_score: Optional[float] = None
    best_practices_score: Optional[float] = None
    seo_issues: Optional[List[str]] = None
    performance_issues: Optional[List[str]] = None
    accessibility_issues: Optional[List[str]] = None
    llm_suggestions: Optional[str] = None
    analyzed_at: Optional[datetime] = None
    analysis_duration: Optional[float] = None  # seconds
    raw_lighthouse_data: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        data = asdict(self)
        if self.analyzed_at:
            data['analyzed_at'] = self.analyzed_at.isoformat()
        if self.seo_issues:
            data['seo_issues'] = json.dumps(self.seo_issues)
        if self.performance_issues:
            data['performance_issues'] = json.dumps(self.performance_issues)
        if self.accessibility_issues:
            data['accessibility_issues'] = json.dumps(self.accessibility_issues)
        if self.raw_lighthouse_data:
            data['raw_lighthouse_data'] = json.dumps(self.raw_lighthouse_data)
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'WebsiteAnalysis':
        """Create from dictionary."""
        if 'analyzed_at' in data and data['analyzed_at']:
            if isinstance(data['analyzed_at'], str):
                data['analyzed_at'] = datetime.fromisoformat(data['analyzed_at'])
        
        for field in ['seo_issues', 'performance_issues', 'accessibility_issues']:
            if field in data and isinstance(data[field], str):
                data[field] = json.loads(data[field])
        
        if 'raw_lighthouse_data' in data and isinstance(data['raw_lighthouse_data'], str):
            data['raw_lighthouse_data'] = json.loads(data['raw_lighthouse_data'])
            
        return cls(**data)


@dataclass
class EmailCampaign:
    """Email campaign data model."""
    id: Optional[int] = None
    lead_id: int = 0
    subject: str = ""
    email_content: str = ""
    email_html: Optional[str] = None
    sent_at: Optional[datetime] = None
    status: str = EmailStatus.PENDING.value
    bounce_reason: Optional[str] = None
    opened_at: Optional[datetime] = None
    clicked_at: Optional[datetime] = None
    replied_at: Optional[datetime] = None
    unsubscribed_at: Optional[datetime] = None
    template_used: Optional[str] = None
    personalization_data: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        data = asdict(self)
        for field in ['sent_at', 'opened_at', 'clicked_at', 'replied_at', 'unsubscribed_at']:
            if data[field]:
                data[field] = data[field].isoformat()
        if self.personalization_data:
            data['personalization_data'] = json.dumps(self.personalization_data)
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'EmailCampaign':
        """Create from dictionary."""
        for field in ['sent_at', 'opened_at', 'clicked_at', 'replied_at', 'unsubscribed_at']:
            if field in data and data[field]:
                if isinstance(data[field], str):
                    data[field] = datetime.fromisoformat(data[field])
        
        if 'personalization_data' in data and isinstance(data['personalization_data'], str):
            data['personalization_data'] = json.loads(data['personalization_data'])
            
        return cls(**data)


Base = declarative_base()

class Lead(Base):
    __tablename__ = 'leads'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(500), nullable=False)
    phone = Column(String(100))
    website = Column(String(1000))
    email = Column(String(255))
    location = Column(String(500))
    business_type = Column(String(200))
    scraped_at = Column(DateTime, default=datetime.utcnow)
    status = Column(String(50), default='new')
    notes = Column(Text)
    is_contacted = Column(Boolean, default=False)
    contacted_at = Column(DateTime)

class ScrapingJob(Base):
    __tablename__ = 'scraping_jobs'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    job_id = Column(String(255), nullable=False)  # UUID for job tracking
    search_term = Column(String(255), nullable=False)
    status = Column(String(50), default='pending')  # pending, running, completed, failed
    progress = Column(Integer, default=0)
    total_listings = Column(Integer, default=0)
    successful_extractions = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime)
    error_message = Column(Text)

class EmailCampaign(Base):
    __tablename__ = 'email_campaigns'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False)
    status = Column(String(50), default='draft')  # draft, running, completed, failed
    sent_count = Column(Integer, default=0)
    total_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime)
    template_id = Column(String(100))
    subject_line = Column(String(255))

class WebsiteAnalysis(Base):
    __tablename__ = 'website_analysis'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    lead_id = Column(Integer, nullable=False)
    lighthouse_score = Column(Integer)
    seo_score = Column(Integer)
    performance_score = Column(Integer)
    accessibility_score = Column(Integer)
    best_practices_score = Column(Integer)
    analysis_data = Column(Text)  # JSON string of detailed analysis
    analyzed_at = Column(DateTime, default=datetime.utcnow)
    status = Column(String(50), default='pending')

# Database connection
def get_database_url():
    """Get database URL from environment or use default SQLite."""
    settings = get_settings()
    return f"sqlite:///{settings.get_full_database_path()}"

def create_engine_and_session():
    """Create database engine and session."""
    database_url = get_database_url()
    engine = create_engine(database_url, connect_args={"check_same_thread": False})
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return engine, SessionLocal

def init_db():
    """Initialize database tables."""
    engine, _ = create_engine_and_session()
    Base.metadata.create_all(bind=engine)
    print("✅ Database tables created successfully!")

def get_db():
    """Get database session."""
    engine, SessionLocal = create_engine_and_session()
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


if __name__ == "__main__":
    # Initialize database
    init_db() 
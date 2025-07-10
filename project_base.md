# PitchPerfect AI - Lead Generation & Scraping Platform

## Project Overview

PitchPerfect AI is a comprehensive lead generation and scraping platform that combines web scraping, data analysis, and email automation. The platform is designed to help businesses find and engage with potential leads through automated scraping of business directories and subsequent outreach campaigns.

## Current Architecture

### Backend (FastAPI + SQLite)
- **Framework**: FastAPI with SQLAlchemy ORM
- **Database**: SQLite (local development) / PostgreSQL (production ready)
- **Scraping Engine**: Playwright-based web scraping with proxy rotation
- **Real-time Updates**: WebSocket-like polling for job status and progress
- **API Design**: RESTful API with standardized response format `{"data": ...}`

### Frontend (React + TypeScript + Vite)
- **Framework**: React 18 with TypeScript
- **Styling**: Tailwind CSS with dark theme
- **Build Tool**: Vite
- **State Management**: React hooks (useState, useEffect)
- **UI Components**: Custom components with Lucide React icons

## Core Features (Implemented)

### 1. Lead Scraping System
- **Google Maps Scraper**: Primary scraping source using Playwright
- **Real-time Progress**: Live updates during scraping with progress bars
- **Job Management**: Start, monitor, and cancel scraping jobs
- **Data Extraction**: Business names, phone numbers, websites, emails, addresses
- **Rate Limiting**: Human-like delays and proxy rotation to avoid detection

### 2. Job History & Management
- **Job Tracking**: Complete job history with status tracking
- **Real-time Monitoring**: Live progress updates for running jobs
- **Job Cancellation**: Ability to stop running jobs
- **Results Export**: CSV export functionality for scraped leads
- **Detailed Views**: Individual job details with lead lists

### 3. Database Schema
```sql
-- Scraping Jobs
ScrapingJob (
  id (Primary Key),
  job_id (UUID),
  search_term,
  source (google_maps),
  status (running/completed/failed/cancelled),
  progress,
  total_listings,
  successful_extractions,
  business_type,
  location,
  created_at,
  completed_at,
  error_message
)

-- Leads
Lead (
  id (Primary Key),
  name,
  phone,
  website,
  email,
  location,
  business_type,
  scraped_at,
  status
)
```

### 4. API Endpoints
- `POST /api/scraping/start` - Start new scraping job
- `GET /api/scraping/status/{job_id}` - Get job status
- `GET /api/scraping/jobs` - List all jobs
- `GET /api/scraping/jobs/{job_id}/leads` - Get leads for job
- `DELETE /api/scraping/jobs/{job_id}` - Cancel job

## Technical Implementation Details

### Scraping Engine
- **Playwright**: Headless browser automation for dynamic content
- **Proxy Rotation**: 41,000+ proxies from multiple sources
- **Human Simulation**: Random delays, mouse movements, scrolling
- **Error Handling**: Graceful failure handling with retry logic
- **Data Validation**: Phone number cleaning, website validation

### Real-time Updates
- **Polling Mechanism**: 2-second intervals for job status
- **Memory Storage**: Active jobs stored in memory for fast access
- **Database Sync**: Jobs persisted to database for history
- **Progress Tracking**: Real-time extraction counts and progress bars

### Frontend Architecture
- **Component Structure**: Modular React components
- **Responsive Design**: Mobile-first approach with Tailwind
- **Dark Theme**: Consistent dark theme with blue accents
- **Error Handling**: Comprehensive error states and user feedback
- **Loading States**: Spinners and progress indicators

## Current Status

### ✅ Completed Features
1. **Core Scraping**: Google Maps scraper fully functional
2. **Job Management**: Complete job lifecycle management
3. **Real-time Updates**: Live progress monitoring
4. **Database Integration**: SQLite with proper schema
5. **Frontend UI**: Modern, responsive interface
6. **API Design**: RESTful API with proper error handling
7. **Export Functionality**: CSV export for leads
8. **Job History**: Complete job tracking and history
9. **Error Handling**: Comprehensive error management
10. **Proxy System**: Large proxy pool with rotation

### 🔄 In Progress
- None currently

### 📋 Planned Features (Not Implemented)
1. **Email Campaign System**: Automated email outreach
2. **Website Analysis**: Lighthouse-based website analysis
3. **Lead Scoring**: AI-powered lead prioritization
4. **CRM Integration**: Third-party CRM connections
5. **Advanced Analytics**: Detailed reporting and insights
6. **Multi-source Scraping**: Additional scraping sources
7. **Email Templates**: Customizable email templates
8. **Campaign Management**: Email campaign tracking

## Development Setup

### Prerequisites
- Python 3.11+
- Node.js 18+
- npm or yarn

### Backend Setup
```bash
# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# or
.venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt

# Start backend server
python server.py
```

### Frontend Setup
```bash
cd frontend
npm install
npm run dev
```

### Environment Configuration
Copy `config_example.env` to `.env` and configure:
- Database settings
- Proxy settings
- Email settings (for future features)

## Production Deployment

### Database
- **Development**: SQLite (current)
- **Production**: PostgreSQL recommended
- **Migration**: Database schema is version-controlled

### Backend Deployment
- **Framework**: FastAPI with Uvicorn
- **Process Manager**: Gunicorn + Uvicorn workers
- **Reverse Proxy**: Nginx recommended
- **Environment**: Docker containerization ready

### Frontend Deployment
- **Build**: `npm run build` creates optimized build
- **Hosting**: Any static hosting (Vercel, Netlify, etc.)
- **API Proxy**: Configure CORS and proxy settings

### Security Considerations
- **Rate Limiting**: Implemented in scraping engine
- **Input Validation**: Pydantic models for API validation
- **Error Handling**: Comprehensive error management
- **Proxy Rotation**: Anti-detection measures

## File Structure

```
PitchPerfect AI/
├── server.py                 # Main backend entry point
├── requirements.txt          # Python dependencies
├── config_example.env        # Environment configuration template
├── project_base.md          # This file - project documentation
├── frontend/                # React frontend
│   ├── src/
│   │   ├── components/      # React components
│   │   ├── services/        # API service layer
│   │   └── main.tsx        # App entry point
│   ├── package.json
│   └── vite.config.ts
├── src/                     # Backend source code
│   ├── api/                 # FastAPI routers
│   ├── scraper/             # Scraping engine
│   ├── database/            # Database models and operations
│   ├── utils/               # Utility functions
│   └── config/              # Configuration management
├── data/                    # Database and data files
│   ├── pitchperfect.db      # SQLite database
│   ├── emails/              # Email templates (future)
│   ├── leads/               # Lead data exports
│   └── reports/             # Generated reports (future)
└── logs/                    # Application logs
    └── pitchperfect.log
```

## API Response Format

All API responses follow a standardized format:
```json
{
  "data": {
    // Response data here
  },
  "success": true,
  "timestamp": "2025-07-11T00:00:00Z"
}
```

## Error Handling

### Backend Errors
- **Validation Errors**: Pydantic model validation
- **Database Errors**: SQLAlchemy exception handling
- **Scraping Errors**: Graceful failure with retry logic
- **Network Errors**: Proxy rotation and timeout handling

### Frontend Errors
- **API Errors**: Axios interceptors for error handling
- **Validation Errors**: Form validation with user feedback
- **Network Errors**: Offline state handling
- **Loading States**: Comprehensive loading indicators

## Performance Considerations

### Scraping Performance
- **Concurrent Scraping**: ThreadPoolExecutor for parallel processing
- **Memory Management**: Efficient data structures and cleanup
- **Rate Limiting**: Human-like delays to avoid detection
- **Proxy Rotation**: Large proxy pool for IP rotation

### Frontend Performance
- **Lazy Loading**: Component-based code splitting
- **Optimized Builds**: Vite for fast development and builds
- **Efficient Polling**: Optimized API polling intervals
- **Memory Management**: Proper cleanup of intervals and listeners

## Monitoring and Logging

### Backend Logging
- **Structured Logging**: Loguru for comprehensive logging
- **Log Levels**: DEBUG, INFO, WARNING, ERROR
- **File Rotation**: Automatic log file management
- **Error Tracking**: Detailed error context and stack traces

### Frontend Logging
- **Console Logging**: Development debugging
- **Error Boundaries**: React error boundary implementation
- **Performance Monitoring**: React DevTools integration

## Future Development Roadmap

### Phase 1: Email System (Next Priority)
- Email template engine
- Campaign management
- Email tracking and analytics
- SMTP integration

### Phase 2: Analysis Engine
- Website analysis with Lighthouse
- Lead scoring algorithms
- Data enrichment
- Competitor analysis

### Phase 3: Advanced Features
- CRM integrations
- Advanced analytics dashboard
- Multi-source scraping
- AI-powered insights

## Troubleshooting

### Common Issues
1. **Port Conflicts**: Backend (8000), Frontend (5173/5174)
2. **Database Issues**: SQLite file permissions
3. **Scraping Failures**: Proxy or rate limiting issues
4. **Frontend Build**: Node.js version compatibility

### Debug Commands
```bash
# Check backend status
curl http://localhost:8000/api/scraping/jobs

# Check frontend
curl http://localhost:5173

# View logs
tail -f logs/pitchperfect.log
```

## Contributing

### Code Standards
- **Python**: PEP 8 with Black formatting
- **TypeScript**: Strict mode with ESLint
- **React**: Functional components with hooks
- **API**: RESTful design with proper HTTP status codes

### Testing Strategy
- **Backend**: Unit tests for core functions
- **Frontend**: Component testing with React Testing Library
- **Integration**: API endpoint testing
- **E2E**: Playwright for end-to-end testing

This documentation serves as the complete knowledge base for the PitchPerfect AI project. All technical decisions, current state, and future plans are documented here for seamless development and maintenance. 
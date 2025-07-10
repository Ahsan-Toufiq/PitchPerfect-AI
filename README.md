# 🚀 PitchPerfect AI - Lead Generation & Scraping Platform

A comprehensive lead generation and scraping platform that combines web scraping, real-time job monitoring, and email automation. Built with FastAPI, React, and modern web technologies.

![PitchPerfect AI](https://img.shields.io/badge/PitchPerfect-AI-blue?style=for-the-badge&logo=python)
![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white)
![React](https://img.shields.io/badge/React-20232A?style=for-the-badge&logo=react&logoColor=61DAFB)
![TypeScript](https://img.shields.io/badge/TypeScript-007ACC?style=for-the-badge&logo=typescript&logoColor=white)

## ✨ Features

### 🔍 **Advanced Lead Scraping**
- **Google Maps Integration**: Scrape business leads from Google Maps with real-time progress
- **Smart Data Extraction**: Extract business names, phone numbers, websites, emails, and addresses
- **Anti-Detection**: Proxy rotation with 41,000+ proxies and human-like behavior simulation
- **Rate Limiting**: Intelligent delays and request management to avoid blocking

### 📊 **Real-Time Job Monitoring**
- **Live Progress Tracking**: Real-time progress bars and status updates
- **Job History**: Complete job lifecycle management with detailed history
- **Job Cancellation**: Stop running jobs at any time
- **Export Functionality**: CSV export for scraped leads

### 🎯 **Modern Web Interface**
- **Responsive Design**: Works seamlessly on desktop, tablet, and mobile
- **Dark Theme**: Beautiful dark theme with modern UI components
- **Real-Time Updates**: Live data updates without page refresh
- **Intuitive Navigation**: Clean, user-friendly interface

### 🛠️ **Robust Backend**
- **FastAPI Framework**: High-performance API with automatic documentation
- **SQLite Database**: Lightweight, reliable data storage
- **RESTful API**: Standardized API responses with proper error handling
- **Background Processing**: Asynchronous job processing

## 🏗️ Architecture

```
PitchPerfect AI/
├── Backend (FastAPI + SQLite)
│   ├── Scraping Engine (Playwright)
│   ├── Job Management System
│   ├── Real-time Progress Tracking
│   └── RESTful API
├── Frontend (React + TypeScript)
│   ├── Lead Scraping Interface
│   ├── Job History Dashboard
│   ├── Real-time Monitoring
│   └── Export Functionality
└── Database (SQLite)
    ├── Scraping Jobs
    └── Lead Data
```

## 🚀 Quick Start

### Prerequisites
- **Python 3.11+**
- **Node.js 18+**
- **npm or yarn**

### Backend Setup

1. **Clone the repository**
```bash
git clone https://github.com/Ahsan-Toufiq/PitchPerfect-AI.git
cd PitchPerfect-AI
```

2. **Create virtual environment**
```bash
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# or
.venv\Scripts\activate  # Windows
```

3. **Install dependencies**
```bash
pip install -r requirements.txt
```

4. **Start the backend server**
```bash
python server.py
```

The backend will be available at `http://localhost:8000`

### Frontend Setup

1. **Navigate to frontend directory**
```bash
cd frontend
```

2. **Install dependencies**
```bash
npm install
```

3. **Start the development server**
```bash
npm run dev
```

The frontend will be available at `http://localhost:5173` (or 5174 if 5173 is in use)

## 📖 Usage

### 1. Start a Scraping Job

1. **Navigate to "Lead Scraping" tab**
2. **Enter business type** (e.g., "restaurants", "coffee shops", "gyms")
3. **Enter location** (e.g., "New York, NY", "Dubai, UAE")
4. **Click "Start Scraping"**

### 2. Monitor Progress

- **Real-time progress bar** shows extraction progress
- **Live statistics** display total listings and successful extractions
- **Status updates** provide detailed information about the scraping process

### 3. View Results

- **Job History tab** shows all completed and running jobs
- **Click on any job** to view detailed results
- **Export to CSV** for further analysis

### 4. Job Management

- **Cancel running jobs** at any time
- **Monitor multiple jobs** simultaneously
- **View job history** with detailed statistics

## 🔧 API Endpoints

### Scraping Endpoints
- `POST /api/scraping/start` - Start new scraping job
- `GET /api/scraping/status/{job_id}` - Get job status
- `GET /api/scraping/jobs` - List all jobs
- `GET /api/scraping/jobs/{job_id}/leads` - Get leads for job
- `DELETE /api/scraping/jobs/{job_id}` - Cancel job

### Dashboard Endpoints
- `GET /api/dashboard/stats` - Get dashboard statistics
- `GET /api/leads` - Get all leads
- `GET /api/leads/export` - Export leads to CSV

## 🛡️ Features & Capabilities

### **Scraping Engine**
- ✅ **Google Maps Integration**: Primary scraping source
- ✅ **Proxy Rotation**: 41,000+ proxies from multiple sources
- ✅ **Human Simulation**: Random delays, mouse movements, scrolling
- ✅ **Error Handling**: Graceful failure handling with retry logic
- ✅ **Data Validation**: Phone number cleaning, website validation

### **Job Management**
- ✅ **Real-time Monitoring**: Live progress updates every 2 seconds
- ✅ **Job Cancellation**: Stop running jobs instantly
- ✅ **Job History**: Complete job lifecycle tracking
- ✅ **Export Functionality**: CSV export with proper formatting

### **User Interface**
- ✅ **Responsive Design**: Mobile-first approach
- ✅ **Dark Theme**: Consistent dark theme with blue accents
- ✅ **Real-time Updates**: Live data without page refresh
- ✅ **Error Handling**: Comprehensive error states and user feedback

### **Backend Architecture**
- ✅ **FastAPI**: High-performance async framework
- ✅ **SQLite Database**: Reliable data storage
- ✅ **RESTful API**: Standardized response format
- ✅ **Background Processing**: Asynchronous job execution

## 📊 Database Schema

### ScrapingJob
```sql
- id (Primary Key)
- job_id (UUID)
- search_term
- source (google_maps)
- status (running/completed/failed/cancelled)
- progress
- total_listings
- successful_extractions
- business_type
- location
- created_at
- completed_at
- error_message
```

### Lead
```sql
- id (Primary Key)
- name
- phone
- website
- email
- location
- business_type
- scraped_at
- status
```

## 🚀 Deployment

### Development
```bash
# Backend
python server.py

# Frontend
cd frontend && npm run dev
```

### Production
```bash
# Backend
pip install gunicorn
gunicorn server:app -w 4 -k uvicorn.workers.UvicornWorker

# Frontend
cd frontend && npm run build
```

## 🔮 Roadmap

### Phase 2A: Email Campaign System
- Email template engine with dynamic variables
- Campaign management and scheduling
- SMTP integration with tracking
- Response and bounce handling

### Phase 2B: Website Analysis Engine
- Lighthouse integration for performance/SEO analysis
- Content and technology stack analysis
- Competitive analysis features

### Phase 2C: Lead Scoring & Intelligence
- AI-powered lead scoring algorithms
- Data enrichment and predictive analytics
- Personalization recommendations

### Phase 2D: Advanced Analytics & Reporting
- Comprehensive dashboard analytics
- Custom reporting and data visualization
- Performance monitoring

### Phase 2E: Integration & Automation
- CRM integrations (HubSpot, Salesforce)
- Automation workflows
- Third-party tool integrations

## 🤝 Contributing

1. **Fork the repository**
2. **Create a feature branch** (`git checkout -b feature/amazing-feature`)
3. **Commit your changes** (`git commit -m 'Add amazing feature'`)
4. **Push to the branch** (`git push origin feature/amazing-feature`)
5. **Open a Pull Request**

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- **FastAPI** for the high-performance backend framework
- **React** for the modern frontend framework
- **Playwright** for reliable web scraping
- **Tailwind CSS** for the beautiful UI components

## 📞 Support

If you have any questions or need support:

- **Create an issue** on GitHub
- **Check the documentation** in `project_base.md`
- **Review the API documentation** at `http://localhost:8000/docs`

---

[![GitHub stars](https://img.shields.io/github/stars/Ahsan-Toufiq/PitchPerfect-AI?style=social)](https://github.com/Ahsan-Toufiq/PitchPerfect-AI)
[![GitHub forks](https://img.shields.io/github/forks/Ahsan-Toufiq/PitchPerfect-AI?style=social)](https://github.com/Ahsan-Toufiq/PitchPerfect-AI)
[![GitHub issues](https://img.shields.io/github/issues/Ahsan-Toufiq/PitchPerfect-AI)](https://github.com/Ahsan-Toufiq/PitchPerfect-AI/issues) 

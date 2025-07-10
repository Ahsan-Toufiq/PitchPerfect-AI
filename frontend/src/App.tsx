import React, { useState, useEffect } from 'react'
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom'
import { ThemeProvider } from './contexts/ThemeContext'
import Layout from './components/Layout'
import Dashboard from './components/Dashboard'
import LeadScraping from './components/LeadScraping'
import JobHistory from './components/JobHistory'
import EmailCampaigns from './components/EmailCampaigns'
import WebsiteAnalysis from './components/WebsiteAnalysis'
import Settings from './components/Settings'
import './App.css'

function App() {
  return (
    <ThemeProvider>
      <Router>
        <div className="min-h-screen bg-gray-900 text-white">
          <Layout>
            <Routes>
              <Route path="/" element={<Dashboard />} />
              <Route path="/scraping" element={<LeadScraping />} />
              <Route path="/history" element={<JobHistory />} />
              <Route path="/emails" element={<EmailCampaigns />} />
              <Route path="/analysis" element={<WebsiteAnalysis />} />
              <Route path="/settings" element={<Settings />} />
            </Routes>
    </Layout>
        </div>
      </Router>
    </ThemeProvider>
  )
}

export default App

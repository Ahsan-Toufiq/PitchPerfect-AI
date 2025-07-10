import React, { useState, useEffect } from 'react'
import { Search, Play, Pause, CheckCircle, AlertCircle, Square, RefreshCw } from 'lucide-react'
import { api } from '../services/api'

interface ScrapingJob {
  id?: number
  job_id: string
  status: string
  progress: number
  total_listings: number
  successful_extractions: number
  message: string
  start_time?: string
}

const LeadScraping: React.FC = () => {
  const [businessType, setBusinessType] = useState('')
  const [location, setLocation] = useState('')
  const [currentJob, setCurrentJob] = useState<ScrapingJob | null>(null)
  const [isLoading, setIsLoading] = useState(false)
  const [isStopping, setIsStopping] = useState(false)
  const [error, setError] = useState('')
  const [runningJobs, setRunningJobs] = useState<ScrapingJob[]>([])

  // Load running jobs on component mount
  useEffect(() => {
    loadRunningJobs()
  }, [])

  const loadRunningJobs = async () => {
    try {
      const response = await api.get('/api/scraping/jobs')
      const jobs = response.data.data
      const running = jobs.filter((job: any) => job.status === 'running')
      setRunningJobs(running)
      
      // If there's a running job and no current job, set the first running job as current
      if (running.length > 0 && !currentJob) {
        const firstRunningJob = running[0]
      setCurrentJob({
          id: firstRunningJob.id,
          job_id: firstRunningJob.job_id,
          status: firstRunningJob.status,
          progress: firstRunningJob.progress,
          total_listings: firstRunningJob.total_listings,
          successful_extractions: firstRunningJob.successful_extractions,
          message: `Monitoring job: ${firstRunningJob.search_term}`
        })
      }
    } catch (err) {
      console.error('Error loading running jobs:', err)
    }
  }

  // Poll for job status
  useEffect(() => {
    if (!currentJob) {
      return
    }

    const interval = setInterval(async () => {
      try {
        console.log('Polling job status for:', currentJob.job_id)
        const response = await api.get(`/api/scraping/status/${currentJob.job_id}`)
        const updatedJob = response.data.data
        console.log('Updated job status:', updatedJob)
        setCurrentJob(updatedJob)
        
        // Refresh running jobs list
        await loadRunningJobs()
        
        // If job is completed, clear current job after a delay
        if (updatedJob.status === 'completed' || updatedJob.status === 'failed' || updatedJob.status === 'cancelled') {
          setTimeout(() => {
            setCurrentJob(null)
          }, 5000) // Clear after 5 seconds
        }
      } catch (err) {
        console.error('Error polling job status:', err)
      }
    }, 2000)

    return () => clearInterval(interval)
  }, [currentJob])

  const handleStartScraping = async () => {
    if (!businessType || !location) {
      setError('Please provide both business type and location')
      return
    }

    setIsLoading(true)
    setError('')
    setCurrentJob(null)

    try {
      const searchTerm = `${businessType} in ${location}`
      const requestData = { 
        search_term: searchTerm,
        source: 'google',
        max_leads: 100,
        business_type: businessType,
        location: location
      }

      const response = await api.post('/api/scraping/start', requestData)
      setCurrentJob({
        id: response.data.data.id,
        job_id: response.data.data.job_id,
        status: response.data.data.status,
        progress: 0,
        total_listings: 0,
        successful_extractions: 0,
        message: response.data.data.message
      })
    } catch (err: any) {
      console.error('Scraping error:', err.response?.data)
      
      // Handle validation errors properly
      if (err.response?.data?.detail) {
        if (Array.isArray(err.response.data.detail)) {
          // Handle validation error array
          const validationErrors = err.response.data.detail.map((error: any) => error.msg).join(', ')
          setError(validationErrors)
        } else {
          // Handle single error message
          setError(err.response.data.detail)
        }
      } else {
        setError('Failed to start scraping job')
      }
    } finally {
      setIsLoading(false)
    }
  }

  const handleStopJob = async () => {
    if (!currentJob) return

    setIsStopping(true)
    try {
      await api.delete(`/api/scraping/jobs/${currentJob.job_id}`)
      setCurrentJob(prev => prev ? { ...prev, status: 'cancelled' } : null)
    } catch (err) {
      console.error('Error stopping job:', err)
    } finally {
      setIsStopping(false)
    }
  }

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'completed':
        return <CheckCircle className="h-5 w-5 text-green-500" />
      case 'failed':
        return <AlertCircle className="h-5 w-5 text-red-500" />
      case 'cancelled':
        return <Square className="h-5 w-5 text-orange-500" />
      case 'running':
        return <Play className="h-5 w-5 text-blue-500 animate-pulse" />
      default:
        return <Pause className="h-5 w-5 text-gray-500" />
    }
  }

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'completed':
        return 'text-green-500'
      case 'failed':
        return 'text-red-500'
      case 'cancelled':
        return 'text-orange-500'
      case 'running':
        return 'text-blue-500'
      default:
        return 'text-gray-500'
    }
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-white">Lead Scraping</h1>
          <p className="text-gray-400 mt-2">Start new scraping jobs and monitor progress</p>
        </div>
              <button
          onClick={loadRunningJobs}
          className="flex items-center px-3 py-2 bg-gray-700 text-white rounded-lg hover:bg-gray-600"
        >
          <RefreshCw className="h-4 w-4 mr-2" />
          Refresh Running Jobs
            </button>
      </div>

      {/* Running Jobs Section */}
      {runningJobs.length > 0 && (
        <div className="bg-gray-800 rounded-lg p-6">
          <h2 className="text-xl font-semibold text-white mb-4">Currently Running Jobs</h2>
          <div className="space-y-3">
            {runningJobs.map((job) => (
              <div key={job.job_id} className="bg-gray-700 rounded-lg p-4">
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center space-x-2">
                    <Play className="h-5 w-5 text-blue-500 animate-pulse" />
                    <span className="text-blue-400 font-medium">{job.search_term}</span>
                  </div>
                  <button
                    onClick={() => {
                      setCurrentJob({
                        id: job.id,
                        job_id: job.job_id,
                        status: job.status,
                        progress: job.progress,
                        total_listings: job.total_listings,
                        successful_extractions: job.successful_extractions,
                        message: `Monitoring job: ${job.search_term}`
                      })
                    }}
                    className="px-3 py-1 bg-blue-600 text-white rounded text-sm hover:bg-blue-700"
                  >
                    Monitor This Job
                  </button>
                </div>
                <div className="text-sm text-gray-400">
                  {job.successful_extractions} leads extracted • {job.total_listings} total listings
            </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Search Form */}
      <div className="bg-gray-800 rounded-lg p-6">
        <h2 className="text-xl font-semibold text-white mb-4">Start New Scraping Job</h2>
        
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
                <div>
            <label className="block text-sm font-medium text-gray-300 mb-2">
              Business Type
                  </label>
                  <input
                    type="text"
              value={businessType}
              onChange={(e) => setBusinessType(e.target.value)}
              placeholder="e.g., restaurants, gyms, coffee shops"
              className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                </div>

                <div>
            <label className="block text-sm font-medium text-gray-300 mb-2">
              Location
                  </label>
                  <input
              type="text"
              value={location}
              onChange={(e) => setLocation(e.target.value)}
              placeholder="e.g., New York, NY"
              className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                </div>
              </div>

        {error && (
          <div className="mb-4 p-3 bg-red-900 border border-red-700 rounded-lg text-red-200">
            {error}
          </div>
        )}

        <button
          onClick={handleStartScraping}
          disabled={isLoading}
          className="flex items-center px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          <Search className="h-5 w-5 mr-2" />
          {isLoading ? 'Starting...' : 'Start Scraping'}
        </button>
            </div>

      {/* Current Job Status */}
      {currentJob && (
        <div className="bg-gray-800 rounded-lg p-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-xl font-semibold text-white">Current Job Progress</h2>
            <div className="flex items-center space-x-4">
              <div className="flex items-center space-x-2">
                {getStatusIcon(currentJob.status)}
                <span className={`font-medium ${getStatusColor(currentJob.status)}`}>
                  {currentJob.status.charAt(0).toUpperCase() + currentJob.status.slice(1)}
                    </span>
              </div>

              {currentJob.status === 'running' && (
                <button
                  onClick={handleStopJob}
                  disabled={isStopping}
                  className="flex items-center px-3 py-1 bg-red-600 text-white rounded-lg hover:bg-red-700 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  <Square className="h-4 w-4 mr-1" />
                  {isStopping ? 'Stopping...' : 'Stop Job'}
                </button>
              )}
            </div>
          </div>
          
          <div className="space-y-4">
            <div>
              <div className="flex justify-between text-sm text-gray-300 mb-1">
                <span>Progress</span>
                <span>{currentJob.successful_extractions} / {currentJob.total_listings > 0 ? currentJob.total_listings : 'Unknown'}</span>
              </div>
              <div className="w-full bg-gray-700 rounded-full h-2">
                <div 
                  className="bg-blue-600 h-2 rounded-full transition-all duration-300"
                  style={{ width: `${currentJob.total_listings > 0 ? (currentJob.successful_extractions / currentJob.total_listings) * 100 : 0}%` }}
                />
              </div>
            </div>

            <div className={`rounded-lg p-3 ${
              currentJob.status === 'running' 
                ? 'bg-blue-900/20 border border-blue-700' 
                : currentJob.status === 'completed'
                ? 'bg-green-900/20 border border-green-700'
                : currentJob.status === 'failed'
                ? 'bg-red-900/20 border border-red-700'
                : currentJob.status === 'cancelled'
                ? 'bg-orange-900/20 border border-orange-700'
                : 'bg-gray-900/20 border border-gray-700'
            }`}>
              <div className="flex items-center space-x-2">
                {currentJob.status === 'running' && (
                  <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-blue-400"></div>
                )}
                {currentJob.status === 'completed' && (
                  <CheckCircle className="h-4 w-4 text-green-400" />
                )}
                {currentJob.status === 'failed' && (
                  <AlertCircle className="h-4 w-4 text-red-400" />
                )}
                {currentJob.status === 'cancelled' && (
                  <Square className="h-4 w-4 text-orange-400" />
                )}
                <span className={`text-sm ${
                  currentJob.status === 'running' ? 'text-blue-300' :
                  currentJob.status === 'completed' ? 'text-green-300' :
                  currentJob.status === 'failed' ? 'text-red-300' :
                  currentJob.status === 'cancelled' ? 'text-orange-300' :
                  'text-gray-300'
                }`}>
                  {currentJob.message}
                </span>
              </div>
            </div>

            <div className="grid grid-cols-3 gap-4 text-sm">
              <div className="bg-gray-700 p-3 rounded-lg">
                <div className="text-gray-400">Total Listings</div>
                <div className="text-white font-semibold">{currentJob.total_listings > 0 ? currentJob.total_listings : 'Unknown'}</div>
              </div>
              <div className="bg-gray-700 p-3 rounded-lg">
                <div className="text-gray-400">Successful</div>
                <div className="text-green-400 font-semibold">{currentJob.successful_extractions}</div>
                        </div>
              <div className="bg-gray-700 p-3 rounded-lg">
                <div className="text-gray-400">Success Rate</div>
                <div className="text-white font-semibold">
                  {currentJob.total_listings > 0 
                    ? `${Math.round((currentJob.successful_extractions / currentJob.total_listings) * 100)}%`
                    : '0%'
                  }
                        </div>
                        </div>
                        </div>

            {/* Info message about Job History */}
            <div className="bg-blue-900/20 border border-blue-700 rounded-lg p-3">
              <div className="flex items-center space-x-2">
                <CheckCircle className="h-4 w-4 text-blue-400" />
                <span className="text-blue-300 text-sm">
                  View detailed results and export leads in the Job History tab
                        </span>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

export default LeadScraping 
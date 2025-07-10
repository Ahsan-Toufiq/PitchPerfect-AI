import React, { useState, useEffect } from 'react'
import { History, Eye, Play, Pause, CheckCircle, AlertCircle, Square, X, Clock, Download } from 'lucide-react'
import { api } from '../services/api'

interface JobHistoryItem {
  id: number
  job_id: string
  search_term: string
  status: string
  progress: number
  total_listings: number
  successful_extractions: number
  created_at: string
  completed_at: string | null
  error_message: string | null
}

interface Lead {
  id: number
  name: string
  phone: string
  website: string
  email: string
  location: string
  business_type: string
  scraped_at: string
  status: string
}

interface JobDetails {
  job: JobHistoryItem
  leads: Lead[]
  isRunning: boolean
}

const JobHistory: React.FC = () => {
  const [jobHistory, setJobHistory] = useState<JobHistoryItem[]>([])
  const [isLoadingHistory, setIsLoadingHistory] = useState(false)
  const [selectedJob, setSelectedJob] = useState<JobDetails | null>(null)
  const [isLoadingDetails, setIsLoadingDetails] = useState(false)
  const [terminatingJobs, setTerminatingJobs] = useState<Set<string>>(new Set())

  // Load job history on component mount
  useEffect(() => {
    loadJobHistory()
  }, [])

  // Poll for job history updates (for running jobs)
  useEffect(() => {
    const interval = setInterval(async () => {
      const runningJobs = jobHistory.filter(job => job.status === 'running')
      if (runningJobs.length > 0) {
        await loadJobHistory()
        
        // Update selected job if it's running
        if (selectedJob && selectedJob.isRunning) {
          await loadJobDetails(selectedJob.job)
        }
      }
    }, 5000)

    return () => clearInterval(interval)
  }, [jobHistory, selectedJob])

  const loadJobHistory = async () => {
    try {
      setIsLoadingHistory(true)
      const response = await api.get('/api/scraping/jobs')
      setJobHistory(response.data.data)
    } catch (err) {
      console.error('Error loading job history:', err)
    } finally {
      setIsLoadingHistory(false)
    }
  }

  const loadJobDetails = async (job: JobHistoryItem) => {
    try {
      setIsLoadingDetails(true)
      console.log('Loading details for job:', job.id)
      
      // Get job info
      const jobInfo = jobHistory.find(j => j.id === job.id)
      if (!jobInfo) return

      // Get leads for this job using database ID
      const leadsResponse = await api.get(`/api/scraping/jobs/${job.id}/leads`)
      console.log('Job leads response:', leadsResponse.data)
      const leads = leadsResponse.data.data.leads || []
      console.log('Found leads:', leads.length)

      setSelectedJob({
        job,
        leads: Array.isArray(leads) ? leads : [],
        isRunning: job.status === 'running'
      })
    } catch (err) {
      console.error('Error loading job details:', err)
      // Set empty leads array on error
      const jobInfo = jobHistory.find(j => j.id === job.id)
      if (jobInfo) {
        setSelectedJob({
          job,
          leads: [],
          isRunning: job.status === 'running'
        })
      }
    } finally {
      setIsLoadingDetails(false)
    }
  }

  const handleViewDetails = async (job: JobHistoryItem) => {
    await loadJobDetails(job)
  }

  const handleStopJob = async (jobId: string) => {
    setTerminatingJobs(prev => new Set(prev).add(jobId))
    
    try {
      await api.delete(`/api/scraping/jobs/${jobId}`)
      await loadJobHistory()
      
      // Update selected job if it's the one being stopped
      if (selectedJob && selectedJob.job.job_id === jobId) {
        setSelectedJob(prev => prev ? { ...prev, job: { ...prev.job, status: 'cancelled' }, isRunning: false } : null)
      }
    } catch (err) {
      console.error('Error stopping job:', err)
    } finally {
      setTerminatingJobs(prev => {
        const newSet = new Set(prev)
        newSet.delete(jobId)
        return newSet
      })
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

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleString()
  }

  const calculateDuration = (createdAt: string, completedAt: string | null) => {
    const start = new Date(createdAt)
    const end = completedAt ? new Date(completedAt) : new Date()
    const diff = end.getTime() - start.getTime()
    const minutes = Math.floor(diff / 60000)
    const seconds = Math.floor((diff % 60000) / 1000)
    return `${minutes}m ${seconds}s`
  }

  const exportToCSV = (leads: Lead[]) => {
    if (leads.length === 0) {
      alert('No leads to export')
      return
    }

    const headers = ['Name', 'Phone', 'Website', 'Email', 'Location', 'Business Type', 'Status', 'Scraped At']
    const csvContent = [
      headers.join(','),
      ...leads.map(lead => [
        `"${lead.name.replace(/"/g, '""')}"`,
        `"${(lead.phone || '').replace(/"/g, '""')}"`,
        `"${(lead.website || '').replace(/"/g, '""')}"`,
        `"${(lead.email || '').replace(/"/g, '""')}"`,
        `"${(lead.location || '').replace(/"/g, '""')}"`,
        `"${(lead.business_type || '').replace(/"/g, '""')}"`,
        `"${lead.status}"`,
        `"${lead.scraped_at}"`
      ].join(','))
    ].join('\n')

    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' })
    const link = document.createElement('a')
    const url = URL.createObjectURL(blob)
    link.setAttribute('href', url)
    link.setAttribute('download', `leads_${new Date().toISOString().split('T')[0]}.csv`)
    link.style.visibility = 'hidden'
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-white">Job History</h1>
          <p className="text-gray-400 mt-2">View all scraping jobs and their results</p>
        </div>
        <button
          onClick={loadJobHistory}
          disabled={isLoadingHistory}
          className="flex items-center px-3 py-2 bg-gray-700 text-white rounded-lg hover:bg-gray-600 disabled:opacity-50"
        >
          <Clock className="h-4 w-4 mr-2" />
          {isLoadingHistory ? 'Refreshing...' : 'Refresh'}
        </button>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Job List */}
        <div className="lg:col-span-1">
          <div className="bg-gray-800 rounded-lg p-6">
            <h2 className="text-xl font-semibold text-white mb-4">All Jobs</h2>
            
            {jobHistory.length === 0 ? (
              <div className="text-center py-8 text-gray-400">
                <History className="h-12 w-12 mx-auto mb-4 opacity-50" />
                <p>No scraping jobs found</p>
              </div>
            ) : (
              <div className="space-y-3">
                {jobHistory.map((job) => (
                  <div 
                    key={job.id} 
                    className={`bg-gray-700 rounded-lg p-4 cursor-pointer transition-colors ${
                      selectedJob?.job.id === job.id ? 'ring-2 ring-blue-500' : 'hover:bg-gray-600'
                    }`}
                    onClick={() => handleViewDetails(job)}
                  >
                    <div className="flex items-center justify-between mb-2">
                      <div className="flex items-center space-x-2">
                        {getStatusIcon(job.status)}
                        <span className={`text-sm font-medium ${getStatusColor(job.status)}`}>
                          {job.status.charAt(0).toUpperCase() + job.status.slice(1)}
                        </span>
                      </div>
                      
                      {job.status === 'running' && (
                        <button
                          onClick={(e) => {
                            e.stopPropagation()
                            handleStopJob(job.job_id)
                          }}
                          disabled={terminatingJobs.has(job.job_id)}
                          className="flex items-center px-2 py-1 bg-red-600 text-white rounded text-xs hover:bg-red-700 disabled:opacity-50"
                        >
                          <X className="h-3 w-3 mr-1" />
                          {terminatingJobs.has(job.job_id) ? 'Stopping...' : 'Stop'}
                        </button>
                      )}
                    </div>
                    
                    <h3 className="text-white font-medium text-sm mb-1">{job.search_term}</h3>
                    <p className="text-gray-400 text-xs">
                      {formatDate(job.created_at)}
                      {job.completed_at && ` - ${calculateDuration(job.created_at, job.completed_at)}`}
                    </p>
                    
                    <div className="flex items-center justify-between mt-2 text-xs text-gray-400">
                      <span>{job.successful_extractions} leads</span>
                      <span>{job.total_listings > 0 ? job.total_listings : 'Unknown'} total</span>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Job Details */}
        <div className="lg:col-span-2">
          {selectedJob ? (
            <div className="bg-gray-800 rounded-lg p-6">
              <div className="flex items-center justify-between mb-4">
                <div>
                  <h2 className="text-xl font-semibold text-white">Job Details</h2>
                  <p className="text-gray-400 text-sm">{selectedJob.job.search_term}</p>
                </div>
                
                <div className="flex items-center space-x-2">
                  {getStatusIcon(selectedJob.job.status)}
                  <span className={`font-medium ${getStatusColor(selectedJob.job.status)}`}>
                    {selectedJob.job.status.charAt(0).toUpperCase() + selectedJob.job.status.slice(1)}
                  </span>
                  
                  {selectedJob.isRunning && (
                    <button
                      onClick={() => handleStopJob(selectedJob.job.job_id)}
                      disabled={terminatingJobs.has(selectedJob.job.job_id)}
                      className="flex items-center px-3 py-1 bg-red-600 text-white rounded-lg hover:bg-red-700 disabled:opacity-50"
                    >
                      <Square className="h-4 w-4 mr-1" />
                      {terminatingJobs.has(selectedJob.job.job_id) ? 'Stopping...' : 'Stop Job'}
                    </button>
                  )}
                </div>
              </div>

              {/* Job Statistics */}
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
                <div className="bg-gray-700 p-3 rounded-lg">
                  <div className="text-gray-400 text-xs">Total Listings</div>
                  <div className="text-white font-semibold">{selectedJob.job.total_listings > 0 ? selectedJob.job.total_listings : 'Unknown'}</div>
                </div>
                <div className="bg-gray-700 p-3 rounded-lg">
                  <div className="text-gray-400 text-xs">Successful</div>
                  <div className="text-green-400 font-semibold">{selectedJob.job.successful_extractions}</div>
                </div>
                <div className="bg-gray-700 p-3 rounded-lg">
                  <div className="text-gray-400 text-xs">Success Rate</div>
                  <div className="text-white font-semibold">
                    {selectedJob.job.total_listings > 0 
                      ? `${Math.round((selectedJob.job.successful_extractions / selectedJob.job.total_listings) * 100)}%`
                      : '0%'
                    }
                  </div>
                </div>
                <div className="bg-gray-700 p-3 rounded-lg">
                  <div className="text-gray-400 text-xs">Duration</div>
                  <div className="text-white font-semibold">
                    {selectedJob.job.completed_at ? 
                      `${Math.round((new Date(selectedJob.job.completed_at).getTime() - new Date(selectedJob.job.created_at).getTime()) / 1000)}s` : 
                      'Running...'
                    }
                  </div>
                </div>
              </div>

              {/* Progress Bar for Running Jobs */}
              {selectedJob.isRunning && (
                <div className="mb-6">
                  <div className="flex justify-between text-sm text-gray-300 mb-1">
                    <span>Progress</span>
                    <span>{selectedJob.job.successful_extractions} / {selectedJob.job.total_listings > 0 ? selectedJob.job.total_listings : 'Unknown'}</span>
                  </div>
                  <div className="w-full bg-gray-700 rounded-full h-2">
                    <div 
                      className="bg-blue-600 h-2 rounded-full transition-all duration-300"
                      style={{ width: `${selectedJob.job.total_listings > 0 ? (selectedJob.job.successful_extractions / selectedJob.job.total_listings) * 100 : 0}%` }}
                    />
                  </div>
                </div>
              )}

              {/* Error Message */}
              {selectedJob.job.error_message && (
                <div className="mb-6 p-3 bg-red-900/20 border border-red-700 rounded text-red-300 text-sm">
                  Error: {selectedJob.job.error_message}
                </div>
              )}

              {/* Leads Table */}
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-lg font-semibold text-white">Scraped Leads</h3>
                <div className="flex space-x-2">
                  {selectedJob.job.successful_extractions > 0 && (!selectedJob.leads || selectedJob.leads.length === 0) && (
                    <button
                      onClick={async () => {
                        try {
                          setIsLoadingDetails(true)
                          const leadsResponse = await api.get(`/api/scraping/jobs/${selectedJob.job.id}/leads`)
                          const leads = leadsResponse.data.data.leads || []
                          setSelectedJob(prev => prev ? { ...prev, leads } : null)
                        } catch (err) {
                          console.error('Error loading leads:', err)
                        } finally {
                          setIsLoadingDetails(false)
                        }
                      }}
                      className="flex items-center px-3 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
                    >
                      <Download className="h-4 w-4 mr-2" />
                      Load Results
                    </button>
                  )}
                  {selectedJob.leads && Array.isArray(selectedJob.leads) && selectedJob.leads.length > 0 && (
                    <button
                      onClick={() => exportToCSV(selectedJob.leads)}
                      className="flex items-center px-3 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700"
                    >
                      <Download className="h-4 w-4 mr-2" />
                      Export CSV
                    </button>
                  )}
                </div>
              </div>

              {isLoadingDetails ? (
                <div className="flex items-center justify-center py-8">
                  <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-blue-400 mr-3"></div>
                  <span className="text-blue-400">Loading leads...</span>
                </div>
              ) : !selectedJob.leads || selectedJob.leads.length === 0 ? (
                <div className="text-center py-8 text-gray-400">
                  <p>
                    {selectedJob.job.successful_extractions > 0 
                      ? 'Click "Load Results" to view the scraped leads'
                      : 'No leads found for this job'
                    }
                  </p>
                </div>
              ) : (
                <div className="border border-gray-700 rounded-lg overflow-hidden">
                  <div className="max-h-96 overflow-y-auto scrollbar-thin scrollbar-thumb-gray-600 scrollbar-track-gray-800">
                    <table className="w-full text-sm">
                      <thead className="sticky top-0 bg-gray-800 z-10">
                        <tr className="border-b border-gray-700">
                          <th className="text-left py-3 px-4 text-gray-300 bg-gray-800">Name</th>
                          <th className="text-left py-3 px-4 text-gray-300 bg-gray-800">Phone</th>
                          <th className="text-left py-3 px-4 text-gray-300 bg-gray-800">Website</th>
                          <th className="text-left py-3 px-4 text-gray-300 bg-gray-800">Email</th>
                          <th className="text-left py-3 px-4 text-gray-300 bg-gray-800">Location</th>
                          <th className="text-left py-3 px-4 text-gray-300 bg-gray-800">Status</th>
                        </tr>
                      </thead>
                      <tbody>
                        {Array.isArray(selectedJob.leads) && selectedJob.leads.map((lead) => (
                          <tr key={lead.id} className="border-b border-gray-700 hover:bg-gray-700 transition-colors duration-150">
                            <td className="py-3 px-4 text-white">{lead.name}</td>
                            <td className="py-3 px-4 text-gray-300">{lead.phone || '-'}</td>
                            <td className="py-3 px-4 text-gray-300">
                              {lead.website ? (
                                <a href={lead.website} target="_blank" rel="noopener noreferrer" className="text-blue-400 hover:underline">
                                  {lead.website}
                                </a>
                              ) : '-'}
                            </td>
                            <td className="py-3 px-4 text-gray-300">{lead.email || '-'}</td>
                            <td className="py-3 px-4 text-gray-300">{lead.location || '-'}</td>
                            <td className="py-3 px-4">
                              <span className="px-2 py-1 text-xs rounded-full bg-green-900 text-green-300">
                                {lead.status}
                              </span>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}
            </div>
          ) : (
            <div className="bg-gray-800 rounded-lg p-6">
              <div className="text-center py-12 text-gray-400">
                <Eye className="h-12 w-12 mx-auto mb-4 opacity-50" />
                <h3 className="text-lg font-medium text-white mb-2">Select a Job</h3>
                <p>Click on any job from the list to view its details and results</p>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

export default JobHistory 
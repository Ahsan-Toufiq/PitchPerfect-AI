import React, { useState, useEffect } from 'react'
import { BarChart3, Users, Mail, Globe, TrendingUp, Activity } from 'lucide-react'
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, LineChart, Line, PieChart, Pie, Cell } from 'recharts'
import { api } from '../services/api'

interface DashboardStats {
  stats: {
    total_leads: number
    total_jobs: number
    completed_jobs: number
    total_campaigns: number
  }
  recent_leads: Array<{
    id: number
    name: string
    phone: string
    website: string
    scraped_at: string
  }>
  recent_jobs: Array<{
    id: number
    search_term: string
    status: string
    progress: number
    created_at: string
  }>
}

const Dashboard: React.FC = () => {
  const [stats, setStats] = useState<DashboardStats | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    fetchDashboardData()
  }, [])

    const fetchDashboardData = async () => {
      try {
      setLoading(true)
      const response = await api.get('/api/dashboard/stats')
      setStats(response.data.data)
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to fetch dashboard data')
      } finally {
      setLoading(false)
      }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500"></div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="bg-red-900 border border-red-700 rounded-lg p-4 text-red-200">
        {error}
      </div>
    )
  }

  if (!stats) {
    return <div>No data available</div>
  }

  // Sample chart data (replace with real data when available)
  const leadGrowthData = [
    { month: 'Jan', leads: 45 },
    { month: 'Feb', leads: 67 },
    { month: 'Mar', leads: 89 },
    { month: 'Apr', leads: 123 },
    { month: 'May', leads: 156 },
    { month: 'Jun', leads: 189 },
  ]

  const jobStatusData = [
    { name: 'Completed', value: stats.stats.completed_jobs, color: '#10B981' },
    { name: 'Running', value: stats.stats.total_jobs - stats.stats.completed_jobs, color: '#3B82F6' },
    { name: 'Failed', value: 2, color: '#EF4444' },
  ]

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold text-white">Dashboard</h1>
        <p className="text-gray-400 mt-2">Overview of your lead generation and outreach activities</p>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <div className="bg-gray-800 rounded-lg p-6">
          <div className="flex items-center">
            <div className="p-2 bg-blue-600 rounded-lg">
              <Users className="h-6 w-6 text-white" />
            </div>
            <div className="ml-4">
              <p className="text-sm font-medium text-gray-400">Total Leads</p>
              <p className="text-2xl font-bold text-white">{stats.stats.total_leads}</p>
            </div>
          </div>
        </div>

        <div className="bg-gray-800 rounded-lg p-6">
          <div className="flex items-center">
            <div className="p-2 bg-green-600 rounded-lg">
              <BarChart3 className="h-6 w-6 text-white" />
            </div>
            <div className="ml-4">
              <p className="text-sm font-medium text-gray-400">Scraping Jobs</p>
              <p className="text-2xl font-bold text-white">{stats.stats.total_jobs}</p>
            </div>
          </div>
        </div>

        <div className="bg-gray-800 rounded-lg p-6">
          <div className="flex items-center">
            <div className="p-2 bg-purple-600 rounded-lg">
              <Mail className="h-6 w-6 text-white" />
            </div>
            <div className="ml-4">
              <p className="text-sm font-medium text-gray-400">Email Campaigns</p>
              <p className="text-2xl font-bold text-white">{stats.stats.total_campaigns}</p>
            </div>
          </div>
        </div>

        <div className="bg-gray-800 rounded-lg p-6">
          <div className="flex items-center">
            <div className="p-2 bg-yellow-600 rounded-lg">
              <TrendingUp className="h-6 w-6 text-white" />
            </div>
            <div className="ml-4">
              <p className="text-sm font-medium text-gray-400">Success Rate</p>
              <p className="text-2xl font-bold text-white">
                {stats.stats.total_jobs > 0 
                  ? `${Math.round((stats.stats.completed_jobs / stats.stats.total_jobs) * 100)}%`
                  : '0%'
                }
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Lead Growth Chart */}
        <div className="bg-gray-800 rounded-lg p-6">
          <h3 className="text-lg font-semibold text-white mb-4">Lead Growth</h3>
          <ResponsiveContainer width="100%" height={300}>
            <LineChart data={leadGrowthData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
              <XAxis dataKey="month" stroke="#9CA3AF" />
              <YAxis stroke="#9CA3AF" />
              <Tooltip 
                contentStyle={{ 
                  backgroundColor: '#1F2937', 
                  border: '1px solid #374151',
                  borderRadius: '8px',
                  color: '#F9FAFB'
                }}
              />
              <Line type="monotone" dataKey="leads" stroke="#3B82F6" strokeWidth={2} />
            </LineChart>
          </ResponsiveContainer>
        </div>

        {/* Job Status Chart */}
        <div className="bg-gray-800 rounded-lg p-6">
          <h3 className="text-lg font-semibold text-white mb-4">Job Status Distribution</h3>
          <ResponsiveContainer width="100%" height={300}>
            <PieChart>
              <Pie
                data={jobStatusData}
                cx="50%"
                cy="50%"
                outerRadius={80}
                dataKey="value"
                label={({ name, value }) => `${name}: ${value}`}
              >
                {jobStatusData.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={entry.color} />
                ))}
              </Pie>
              <Tooltip 
                contentStyle={{ 
                  backgroundColor: '#1F2937', 
                  border: '1px solid #374151',
                  borderRadius: '8px',
                  color: '#F9FAFB'
                }}
              />
            </PieChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Recent Activity */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Recent Leads */}
        <div className="bg-gray-800 rounded-lg p-6">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-semibold text-white">Recent Leads</h3>
            <Activity className="h-5 w-5 text-gray-400" />
          </div>
          <div className="space-y-3">
            {stats.recent_leads.slice(0, 5).map((lead) => (
              <div key={lead.id} className="flex items-center justify-between p-3 bg-gray-700 rounded-lg">
                <div>
                  <p className="text-white font-medium">{lead.name}</p>
                  <p className="text-gray-400 text-sm">{lead.phone || 'No phone'}</p>
                </div>
                <div className="text-right">
                  <p className="text-gray-400 text-sm">
                    {new Date(lead.scraped_at).toLocaleDateString()}
                  </p>
                  {lead.website && (
                    <a 
                      href={lead.website} 
                      target="_blank" 
                      rel="noopener noreferrer"
                      className="text-blue-400 text-sm hover:underline"
                    >
                      Website
                    </a>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Recent Jobs */}
        <div className="bg-gray-800 rounded-lg p-6">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-semibold text-white">Recent Jobs</h3>
            <BarChart3 className="h-5 w-5 text-gray-400" />
          </div>
          <div className="space-y-3">
            {stats.recent_jobs.slice(0, 5).map((job) => (
              <div key={job.id} className="p-3 bg-gray-700 rounded-lg">
                <div className="flex items-center justify-between mb-2">
                  <p className="text-white font-medium truncate">{job.search_term}</p>
                  <span className={`px-2 py-1 text-xs rounded-full ${
                    job.status === 'completed' 
                      ? 'bg-green-900 text-green-300'
                      : job.status === 'running'
                      ? 'bg-blue-900 text-blue-300'
                      : 'bg-gray-900 text-gray-300'
                  }`}>
                    {job.status}
                  </span>
                </div>
                <div className="flex items-center justify-between text-sm text-gray-400">
                  <span>Progress: {job.progress}%</span>
                  <span>{new Date(job.created_at).toLocaleDateString()}</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}

export default Dashboard 
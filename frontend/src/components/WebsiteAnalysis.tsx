import React from 'react'
import { Globe, BarChart3, Settings } from 'lucide-react'

const WebsiteAnalysis: React.FC = () => {
  return (
    <div className="space-y-6">
        <div>
        <h1 className="text-3xl font-bold text-white">Website Analysis</h1>
        <p className="text-gray-400 mt-2">Analyze websites for SEO and performance insights</p>
      </div>

      <div className="bg-gray-800 rounded-lg p-6">
        <div className="text-center py-12">
          <Globe className="h-12 w-12 text-gray-400 mx-auto mb-4" />
          <h3 className="text-lg font-medium text-white mb-2">Website Analysis Coming Soon</h3>
          <p className="text-gray-400">This feature is under development and will be available soon.</p>
        </div>
      </div>
    </div>
  )
}

export default WebsiteAnalysis 
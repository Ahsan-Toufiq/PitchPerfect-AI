import React from 'react'
import { Settings as SettingsIcon } from 'lucide-react'

const Settings: React.FC = () => {
  return (
    <div className="space-y-6">
        <div>
        <h1 className="text-3xl font-bold text-white">Settings</h1>
        <p className="text-gray-400 mt-2">Configure your application preferences</p>
      </div>

      <div className="bg-gray-800 rounded-lg p-6">
        <div className="text-center py-12">
          <SettingsIcon className="h-12 w-12 text-gray-400 mx-auto mb-4" />
          <h3 className="text-lg font-medium text-white mb-2">Settings Coming Soon</h3>
          <p className="text-gray-400">This feature is under development and will be available soon.</p>
        </div>
      </div>
    </div>
  )
}

export default Settings 
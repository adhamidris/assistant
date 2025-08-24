'use client'

import { useState, useEffect } from 'react'
import { useSearchParams } from 'next/navigation'
import { Phone, MessageCircle, Bot } from 'lucide-react'
import { createSession, validateSession, getSessionToken, setSessionToken, setContactInfo } from '@/lib/api'
import { formatPhoneNumber, isValidPhoneNumber, toE164Format, getErrorMessage } from '@/lib/utils'
import ChatInterface from '@/components/ChatInterface'

// API Configuration
const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE || 'http://localhost:8000'

export default function CustomerPortal() {
  const [step, setStep] = useState<'phone' | 'chat'>('phone')
  const [phoneNumber, setPhoneNumber] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState('')
  const [sessionData, setSessionData] = useState<any>(null)
  const [workspaceId, setWorkspaceId] = useState<string | null>(null)
  const [workspaceData, setWorkspaceData] = useState<any>(null)
  const [portalStatus, setPortalStatus] = useState<any>(null)
  const [showCreateAgentModal, setShowCreateAgentModal] = useState(false)
  const [agentFormData, setAgentFormData] = useState({
    name: '',
    description: '',
    channel_type: 'website',
    custom_instructions: ''
  })

  const searchParams = useSearchParams()

  useEffect(() => {
    // Get workspace ID from URL parameters
    const wsId = searchParams.get('workspace')
    if (wsId) {
      setWorkspaceId(wsId)
      // Load workspace data and check if we should redirect to custom URL
      loadWorkspaceData(wsId)
    } else {
      setError('Invalid portal link. Missing workspace parameter.')
    }
    
    // Check for existing session on load
    checkExistingSession()
  }, [searchParams])

  const loadWorkspaceData = async (wsId: string) => {
    try {
      // Load workspace data
      const response = await fetch(`${API_BASE_URL}/api/v1/core/workspaces/${wsId}/`)
      if (response.ok) {
        const data = await response.json()
        setWorkspaceData(data)
        
        // Check portal status (agent availability)
        await checkPortalStatus(wsId)
      } else {
        setError('Workspace not found or access denied.')
      }
    } catch (error) {
      console.error('Failed to load workspace data:', error)
      setError('Failed to load workspace information.')
    }
  }

  const checkPortalStatus = async (wsId: string) => {
    try {
      console.log('Checking portal status for workspace:', wsId)
      const response = await fetch(`${API_BASE_URL}/api/v1/core/workspace/${wsId}/portal-status/`)
      console.log('Portal status response:', response.status, response.statusText)
      if (response.ok) {
        const status = await response.json()
        console.log('Portal status data:', status)
        setPortalStatus(status)
      } else {
        console.error('Portal status request failed:', response.status, response.statusText)
        const errorText = await response.text()
        console.error('Error response:', errorText)
      }
    } catch (error) {
      console.error('Failed to check portal status:', error)
    }
  }

  const activateAgent = async (agentId: string) => {
    if (!workspaceId) return
    
    try {
      const response = await fetch(`${API_BASE_URL}/api/v1/core/workspace/${workspaceId}/agents/${agentId}/toggle-active/`, {
        method: 'POST',
        headers: {
          'Authorization': `Token ${localStorage.getItem('authToken')}`
        }
      })
      
      if (response.ok) {
        // Reload portal status
        if (workspaceId) {
          await checkPortalStatus(workspaceId)
        }
      } else {
        alert('Failed to activate agent')
      }
    } catch (error) {
      console.error('Error activating agent:', error)
      alert('Error activating agent')
    }
  }

  const createAgent = async () => {
    if (!workspaceData?.slug || !agentFormData.name.trim()) {
      alert('Please enter an agent name')
      return
    }

    try {
      setIsLoading(true)
      
      // Generate a valid slug
      let slug = agentFormData.name.toLowerCase()
        .replace(/[^a-z0-9\s]/g, '') // Remove special characters except spaces
        .replace(/\s+/g, '-') // Replace spaces with hyphens
        .replace(/^-+|-+$/g, '') // Remove leading/trailing hyphens
      
      // Ensure slug is not empty
      if (!slug) {
        slug = 'agent-' + Date.now()
      }
      
      const requestData = {
        name: agentFormData.name.trim(),
        slug: slug,
        description: agentFormData.description || '',
        channel_type: agentFormData.channel_type || 'website',
        custom_instructions: agentFormData.custom_instructions || '',
        business_context: {},
        personality_config: {}
      }
      
      // Remove workspace from request data since it's determined by URL path
      
      console.log('Creating agent with data:', requestData)
      console.log('Workspace data:', workspaceData)
      console.log('Workspace slug:', workspaceData.slug)
      console.log('Workspace ID:', workspaceId)
      
      const response = await fetch(`${API_BASE_URL}/api/v1/core/workspace/${workspaceId}/agents/`, {
        method: 'POST',
        headers: {
          'Authorization': `Token ${localStorage.getItem('authToken')}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(requestData)
      })
      
      if (response.ok) {
        const newAgent = await response.json()
        
        // Auto-activate the new agent
        await activateAgent(newAgent.id)
        
        // Close modal and reset form
        setShowCreateAgentModal(false)
        setAgentFormData({
          name: '',
          description: '',
          channel_type: 'website',
          custom_instructions: ''
        })
        
        // Reload portal status to update UI
        if (workspaceId) {
          await checkPortalStatus(workspaceId)
        }
      } else {
        const errorData = await response.json()
        console.error('Agent creation failed:', errorData)
        
        // Show more user-friendly error message
        if (errorData.slug && errorData.slug.includes('already exists')) {
          alert('An agent with this name already exists. Please choose a different name.')
        } else if (errorData.name) {
          alert(`Agent name error: ${errorData.name.join(', ')}`)
        } else {
          alert(`Failed to create agent. Please check your input and try again.`)
        }
      }
    } catch (error) {
      console.error('Error creating agent:', error)
      alert('Error creating agent')
    } finally {
      setIsLoading(false)
    }
  }

  const checkExistingSession = async () => {
    const token = getSessionToken()
    if (!token) return

    try {
      setIsLoading(true)
      const response = await validateSession({ session_token: token })
      if (response.valid) {
        // Extract only the fields that ChatInterface expects
        setSessionData({
          contact_id: response.contact_id,
          contact_name: response.contact_name,
          workspace_name: response.workspace_name,
          assistant_name: response.assistant_name
        })
        setStep('chat')
      }
    } catch (error) {
      console.error('Session validation failed:', error)
      // Clear invalid session
      localStorage.removeItem('session_token')
    } finally {
      setIsLoading(false)
    }
  }

  const handlePhoneSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')

    if (!phoneNumber.trim()) {
      setError('Please enter your phone number')
      return
    }

    if (!isValidPhoneNumber(phoneNumber)) {
      setError('Please enter a valid phone number')
      return
    }

    if (!workspaceId) {
      setError('Invalid portal link. Please contact the business owner.')
      return
    }

    try {
      setIsLoading(true)
      const e164Phone = toE164Format(phoneNumber)
      
      const response = await createSession({
        phone_number: e164Phone,
        workspace_id: workspaceId
      })

      // Store session data
      setSessionToken(response.session_token)
      setContactInfo({
        id: response.contact_id,
        name: response.contact_name,
        phone: e164Phone,
        is_new: response.is_new_contact
      })

      // Extract only the fields that ChatInterface expects
      setSessionData({
        contact_id: response.contact_id,
        contact_name: response.contact_name,
        workspace_name: response.workspace_name,
        assistant_name: response.assistant_name
      })
      setStep('chat')
    } catch (error) {
      setError(getErrorMessage(error))
    } finally {
      setIsLoading(false)
    }
  }

  if (isLoading && step === 'phone') {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="w-8 h-8 border-2 border-blue-600 border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
          <p className="text-gray-600">Connecting...</p>
        </div>
      </div>
    )
  }

  if (step === 'chat' && sessionData) {
    return <ChatInterface sessionData={sessionData} />
  }

  if (error && !workspaceId) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center max-w-md mx-auto p-6">
          <div className="w-16 h-16 bg-red-100 rounded-full flex items-center justify-center mx-auto mb-4">
            <Bot className="w-8 h-8 text-red-600" />
          </div>
          <h2 className="text-xl font-semibold text-gray-900 mb-2">Invalid Portal Link</h2>
          <p className="text-gray-600 mb-4">{error}</p>
          <a 
            href="/" 
            className="inline-flex items-center px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
          >
            Return to Homepage
          </a>
        </div>
      </div>
    )
  }

  // Show portal status messages when no active agent
  if (portalStatus && portalStatus.status !== 'active') {
    // Check if this is the business owner (has auth token and user data)
    const authToken = localStorage.getItem('authToken')
    const userData = localStorage.getItem('userData')
    const isOwner = authToken && userData
    
    if (isOwner && (portalStatus.status === 'no_active_agent' || portalStatus.status === 'no_agents')) {
      // Show agent management interface for owners
      return (
        <div className="min-h-screen bg-gray-50 flex items-center justify-center p-4">
          <div className="w-full max-w-md">
            <div className="text-center mb-6">
              <div className="w-16 h-16 bg-blue-100 rounded-full flex items-center justify-center mx-auto mb-4">
                <Bot className="w-8 h-8 text-blue-600" />
              </div>
              <h2 className="text-xl font-semibold text-gray-900 mb-2">
                {portalStatus.status === 'no_agents' ? 'Create Your First AI Agent' : 'No Active AI Agent'}
              </h2>
              <p className="text-gray-600">
                {portalStatus.status === 'no_agents' 
                  ? 'Set up an AI agent to start helping your customers'
                  : 'Activate an agent to enable customer conversations'
                }
              </p>
            </div>
            
            <div className="bg-white rounded-lg shadow-md p-6 space-y-4">
              {portalStatus.status === 'no_active_agent' && portalStatus.inactive_agents?.length > 0 && (
                <>
                  <h3 className="font-medium text-gray-900">Your Inactive Agents:</h3>
                  {portalStatus.inactive_agents.map((agent: any) => (
                    <div key={agent.id} className="flex items-center justify-between p-3 border rounded-lg">
                      <div>
                        <p className="font-medium">{agent.name}</p>
                        <p className="text-sm text-gray-600">{agent.description}</p>
                      </div>
                      <button
                        onClick={() => activateAgent(agent.id)}
                        className="px-3 py-1 bg-green-600 text-white text-sm rounded hover:bg-green-700"
                      >
                        Activate
                      </button>
                    </div>
                  ))}
                </>
              )}
              
              {portalStatus.status === 'no_agents' && (
                <div className="text-center py-4">
                  <Bot className="w-12 h-12 text-gray-400 mx-auto mb-4" />
                  <p className="text-gray-600 mb-4">You haven't created any AI agents yet</p>
                </div>
              )}
              
              <div className="space-y-2">
                <button
                  onClick={() => setShowCreateAgentModal(true)}
                  className="w-full px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
                >
                  {portalStatus.status === 'no_agents' ? 'Create Your First Agent' : 'Create New Agent'}
                </button>
                <button
                  onClick={() => window.location.href = '/dashboard?tab=ai-agents'}
                  className="w-full px-4 py-2 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200"
                >
                  Go to Dashboard
                </button>
              </div>
            </div>
          </div>
        </div>
      )
    }
    
    // Show friendly unavailable message for clients
    return (
      <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 flex items-center justify-center p-4">
        <div className="text-center max-w-md mx-auto">
          <div className="bg-white rounded-2xl shadow-xl p-8">
            <div className="w-20 h-20 bg-gradient-to-br from-blue-500 to-indigo-600 rounded-full flex items-center justify-center mx-auto mb-6 shadow-lg">
              <Bot className="w-10 h-10 text-white" />
            </div>
            <h2 className="text-2xl font-bold text-gray-900 mb-2">
              {workspaceData?.name || 'AI Assistant'}
            </h2>
            <div className="bg-blue-50 border border-blue-200 rounded-xl p-6 mb-6">
              <p className="text-blue-800 font-medium text-lg mb-2">We'll be right back!</p>
              <p className="text-blue-700">
                Our AI assistant is temporarily unavailable. We're working to get it back online soon.
              </p>
            </div>
            <div className="space-y-3 text-sm text-gray-600">
              <p>✨ In the meantime, feel free to reach out directly</p>
              <p>🔄 You can also check back in a few minutes</p>
            </div>
          </div>
        </div>
      </div>
    )
  }

  return (
    <>
      {/* Agent Creation Modal */}
      {showCreateAgentModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
          <div className="bg-white rounded-lg shadow-xl w-full max-w-md">
            <div className="p-6">
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-lg font-semibold text-gray-900">Create AI Agent</h3>
                <button
                  onClick={() => setShowCreateAgentModal(false)}
                  className="text-gray-400 hover:text-gray-600"
                >
                  ✕
                </button>
              </div>
              
              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Agent Name *
                  </label>
                  <input
                    type="text"
                    value={agentFormData.name}
                    onChange={(e) => setAgentFormData({ ...agentFormData, name: e.target.value })}
                    placeholder="e.g., Customer Support Assistant"
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  />
                </div>
                
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Description
                  </label>
                  <textarea
                    value={agentFormData.description}
                    onChange={(e) => setAgentFormData({ ...agentFormData, description: e.target.value })}
                    placeholder="Describe what this agent does..."
                    rows={3}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  />
                </div>
                
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Channel Type
                  </label>
                  <select
                    value={agentFormData.channel_type}
                    onChange={(e) => setAgentFormData({ ...agentFormData, channel_type: e.target.value })}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                    required
                  >
                    <option value="website">Website Chat</option>
                    <option value="whatsapp">WhatsApp</option>
                    <option value="instagram">Instagram</option>
                    <option value="facebook">Facebook Messenger</option>
                    <option value="telegram">Telegram</option>
                    <option value="sms">SMS</option>
                    <option value="email">Email</option>
                    <option value="phone">Phone Call</option>
                  </select>
                </div>
                
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Custom Instructions
                  </label>
                  <textarea
                    value={agentFormData.custom_instructions}
                    onChange={(e) => setAgentFormData({ ...agentFormData, custom_instructions: e.target.value })}
                    placeholder="Any specific instructions for this agent..."
                    rows={3}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  />
                </div>
              </div>
              
              <div className="flex space-x-3 mt-6">
                <button
                  onClick={() => setShowCreateAgentModal(false)}
                  className="flex-1 px-4 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50"
                >
                  Cancel
                </button>
                <button
                  onClick={createAgent}
                  disabled={isLoading}
                  className="flex-1 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
                >
                  {isLoading ? 'Creating...' : 'Create & Activate'}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 flex items-center justify-center p-4">
        <div className="w-full max-w-md">
        {/* Header */}
        <div className="text-center mb-8">
          <div className="w-16 h-16 bg-gradient-to-br from-blue-500 to-indigo-600 rounded-full flex items-center justify-center mx-auto mb-4 shadow-lg">
            <Bot className="w-8 h-8 text-white" />
          </div>
          <h1 className="text-2xl font-bold text-gray-900 mb-2">
            {workspaceData?.name || 'Business'} Support
          </h1>
          <p className="text-gray-600">
            Chat with {workspaceData?.assistant_name || 'our AI assistant'}
          </p>
        </div>

        {/* Phone Input Form */}
        <div className="bg-white rounded-2xl shadow-xl p-6">
          <form onSubmit={handlePhoneSubmit} className="space-y-6">
            {error && (
              <div className="bg-red-50 border border-red-200 rounded-lg p-4">
                <p className="text-red-800 text-sm">{error}</p>
              </div>
            )}

            <div>
              <label htmlFor="phone" className="block text-sm font-medium text-gray-700 mb-2">
                Enter your phone number
              </label>
              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                  <Phone className="h-5 w-5 text-gray-400" />
                </div>
                <input
                  type="tel"
                  id="phone"
                  value={phoneNumber}
                  onChange={(e) => setPhoneNumber(e.target.value)}
                  className="block w-full pl-10 pr-3 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 text-gray-900 placeholder-gray-500"
                  placeholder="+1 (555) 123-4567"
                  disabled={isLoading}
                />
              </div>
              <p className="mt-2 text-xs text-gray-500">
                We'll use this to identify you and continue conversations
              </p>
            </div>

            <button
              type="submit"
              disabled={isLoading || !phoneNumber.trim()}
              className="w-full bg-gradient-to-r from-blue-500 to-indigo-600 text-white py-3 px-4 rounded-lg font-medium hover:from-blue-600 hover:to-indigo-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed transition-all duration-200"
            >
              {isLoading ? (
                <div className="flex items-center justify-center">
                  <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin mr-2"></div>
                  Connecting...
                </div>
              ) : (
                <div className="flex items-center justify-center">
                  <MessageCircle className="w-5 h-5 mr-2" />
                  Start Chat
                </div>
              )}
            </button>
          </form>
        </div>

        {/* Footer */}
        <div className="text-center mt-6">
          <p className="text-sm text-gray-500">
            Powered by AI Personal Business Assistant
          </p>
        </div>
      </div>
    </div>
    </>
  )
}


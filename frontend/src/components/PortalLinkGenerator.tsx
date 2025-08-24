'use client'

import { useState, useEffect } from 'react'
import { 
  Share2, 
  Copy, 
  Check, 
  Share, 
  ExternalLink, 
  User, 
  Building,
  Bot
} from 'lucide-react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Alert, AlertDescription } from '@/components/ui/alert'

// API Configuration
const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE || 'http://localhost:8000'

interface PortalLinkGeneratorProps {
  workspaceId: string
}

interface AgentLink {
  id: string
  name: string
  description: string
  slug: string
  is_active: boolean
  is_default: boolean
  channel_type: string
  portal_url: string
  qr_code_url: string
}

interface PortalData {
  workspace_id: string
  workspace_name: string
  workspace_slug: string
  main_portal_url?: string
  default_agent?: {
    id: string
    name: string
    slug: string
  }
  agent_links: AgentLink[]
  active_agents_count: number
  total_agents_count: number
  instructions: string
  is_business_user: boolean
  user_info: {
    business_name: string | null
    full_name: string
    assistant_name: string
  }
}

export default function PortalLinkGenerator({ workspaceId }: PortalLinkGeneratorProps) {
  const [portalData, setPortalData] = useState<PortalData | null>(null)
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState('')
  const [copied, setCopied] = useState(false)

  useEffect(() => {
    generatePortalLink()
  }, [workspaceId])

  const generatePortalLink = async () => {
    setIsLoading(true)
    setError('')

    try {
      const token = localStorage.getItem('authToken')
      if (!token) {
        setError('Authentication required')
        return
      }

      const response = await fetch(`${API_BASE_URL}/api/v1/auth/portal-link/`, {
        method: 'GET',
        headers: {
          'Authorization': `Token ${token}`,
          'Content-Type': 'application/json',
        }
      })

      if (response.ok) {
        const data = await response.json()
        setPortalData(data)
      } else {
        const errorData = await response.json()
        setError(errorData.error || 'Failed to generate portal link')
      }
    } catch (error) {
      console.error('Error generating portal link:', error)
      setError('Network error. Please try again.')
    } finally {
      setIsLoading(false)
    }
  }

  const copyToClipboard = async (url: string) => {
    try {
      await navigator.clipboard.writeText(url)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    } catch (error) {
      console.error('Failed to copy to clipboard:', error)
      // Fallback for older browsers
      const textArea = document.createElement('textarea')
      textArea.value = url
      document.body.appendChild(textArea)
      textArea.select()
      document.execCommand('copy')
      document.body.removeChild(textArea)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    }
  }

  const shareLink = async (url: string, agentName?: string) => {
    if (navigator.share) {
      try {
        await navigator.share({
          title: `Chat with ${agentName || 'our AI Assistant'}`,
          text: 'Start a conversation with our AI assistant using this link:',
          url: url,
        })
      } catch (error) {
        console.error('Error sharing:', error)
      }
    } else {
      // Fallback to copy
      copyToClipboard(url)
    }
  }

  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center">
            <Share2 className="w-5 h-5 mr-2" />
            Portal Links
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex items-center justify-center py-8">
            <div className="w-6 h-6 border-2 border-blue-600 border-t-transparent rounded-full animate-spin mr-3"></div>
            Generating portal links...
          </div>
        </CardContent>
      </Card>
    )
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center">
          <Share2 className="w-5 h-5 mr-2" />
          Portal Links
        </CardTitle>
        <CardDescription>
          Share these links with your clients to start conversations with your AI agents
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {error && (
          <Alert variant="destructive">
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        )}

        {portalData && (
          <>
            {/* Workspace Info */}
            <div className="bg-gradient-to-r from-blue-50 to-indigo-50 border border-blue-200 rounded-lg p-4 mb-4">
              <div className="flex items-center mb-2">
                {portalData.is_business_user ? (
                  <Building className="w-5 h-5 text-blue-600 mr-2" />
                ) : (
                  <User className="w-5 h-5 text-blue-600 mr-2" />
                )}
                <h4 className="text-sm font-medium text-blue-900">
                  {portalData.workspace_name}
                </h4>
              </div>
              <div className="text-sm text-blue-800 space-y-1">
                <p><strong>Agents:</strong> {portalData.active_agents_count} active, {portalData.total_agents_count} total</p>
                {portalData.default_agent && (
                  <p><strong>Default Agent:</strong> {portalData.default_agent.name}</p>
                )}
              </div>
            </div>

            {/* Main Portal Link (if default agent exists) */}
            {portalData.main_portal_url && portalData.default_agent ? (
              <div className="space-y-3 mb-6">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Main Portal Link (Default Agent: {portalData.default_agent.name})
                  </label>
                  <div className="flex items-center space-x-2">
                    <input
                      type="text"
                      value={portalData.main_portal_url}
                      readOnly
                      className="flex-1 px-3 py-2 bg-gray-50 border border-gray-300 rounded-md text-sm"
                    />
                    <button
                      onClick={() => copyToClipboard(portalData.main_portal_url!)}
                      className="px-3 py-2 bg-blue-600 text-white text-sm rounded-md hover:bg-blue-700 flex items-center"
                    >
                      {copied ? (
                        <>
                          <Check className="w-4 h-4 mr-1" />
                          Copied!
                        </>
                      ) : (
                        <>
                          <Copy className="w-4 h-4 mr-1" />
                          Copy
                        </>
                      )}
                    </button>
                  </div>
                </div>

                <div className="flex space-x-2">
                  <button
                    onClick={() => shareLink(portalData.main_portal_url!, portalData.default_agent?.name)}
                    className="flex-1 px-4 py-2 bg-green-600 text-white text-sm rounded-md hover:bg-green-700 flex items-center justify-center"
                  >
                    <Share className="w-4 h-4 mr-2" />
                    Share Main Link
                  </button>
                  <a
                    href={portalData.main_portal_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="flex-1 px-4 py-2 bg-gray-600 text-white text-sm rounded-md hover:bg-gray-700 flex items-center justify-center"
                  >
                    <ExternalLink className="w-4 h-4 mr-2" />
                    Test Portal
                  </a>
                </div>
              </div>
            ) : (
              <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4 mb-6">
                <p className="text-yellow-800 text-sm">
                  <strong>No main portal link available.</strong> Set an agent as default to enable a main portal link.
                </p>
              </div>
            )}

            {/* Individual Agent Links */}
            <div className="space-y-4">
              <h4 className="text-lg font-medium text-gray-900">Individual Agent Links</h4>
              
              {portalData.agent_links.length === 0 ? (
                <div className="text-center py-8 bg-gray-50 rounded-lg">
                  <Bot className="w-12 h-12 text-gray-400 mx-auto mb-4" />
                  <p className="text-gray-600">No AI agents created yet.</p>
                  <p className="text-sm text-gray-500 mt-1">Create agents in the AI Agents tab to generate portal links.</p>
                </div>
              ) : (
                <div className="space-y-3">
                  {portalData.agent_links.map((agent) => (
                    <div key={agent.id} className="border border-gray-200 rounded-lg p-4">
                      <div className="flex items-center justify-between mb-3">
                        <div className="flex items-center space-x-2">
                          <h5 className="font-medium text-gray-900">{agent.name}</h5>
                          {agent.is_default && (
                            <span className="px-2 py-1 bg-blue-100 text-blue-800 text-xs rounded-full">Default</span>
                          )}
                          <span className={`px-2 py-1 text-xs rounded-full ${
                            agent.is_active 
                              ? 'bg-green-100 text-green-800' 
                              : 'bg-red-100 text-red-800'
                          }`}>
                            {agent.is_active ? 'Active' : 'Inactive'}
                          </span>
                          <span className="px-2 py-1 bg-gray-100 text-gray-700 text-xs rounded-full capitalize">
                            {agent.channel_type}
                          </span>
                        </div>
                      </div>
                      
                      {agent.description && (
                        <p className="text-sm text-gray-600 mb-3">{agent.description}</p>
                      )}

                      <div className="flex items-center space-x-2 mb-2">
                        <input
                          type="text"
                          value={agent.portal_url}
                          readOnly
                          className="flex-1 px-3 py-2 bg-gray-50 border border-gray-300 rounded-md text-sm"
                        />
                        <button
                          onClick={() => copyToClipboard(agent.portal_url)}
                          className="px-3 py-2 bg-blue-600 text-white text-sm rounded-md hover:bg-blue-700 flex items-center"
                        >
                          <Copy className="w-4 h-4 mr-1" />
                          Copy
                        </button>
                      </div>

                      <div className="flex space-x-2">
                        <button
                          onClick={() => shareLink(agent.portal_url, agent.name)}
                          className="px-3 py-2 bg-green-600 text-white text-sm rounded-md hover:bg-green-700 flex items-center"
                        >
                          <Share className="w-4 h-4 mr-1" />
                          Share
                        </button>
                        <a
                          href={agent.portal_url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="px-3 py-2 bg-gray-600 text-white text-sm rounded-md hover:bg-gray-700 flex items-center"
                        >
                          <ExternalLink className="w-4 h-4 mr-1" />
                          Test
                        </a>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* Instructions */}
            <div className="bg-gray-50 rounded-lg p-4">
              <h4 className="text-sm font-medium text-gray-900 mb-2">
                How to use your portal links:
              </h4>
              <ul className="text-sm text-gray-600 space-y-1">
                <li>• <strong>Main Portal Link:</strong> Use when you have a default agent set</li>
                <li>• <strong>Individual Agent Links:</strong> Direct clients to specific AI agents</li>
                <li>• <strong>Active agents only:</strong> Only active agents will respond to conversations</li>
                <li>• Share links via email, SMS, social media, or embed on your website</li>
              </ul>
            </div>
          </>
        )}
      </CardContent>
    </Card>
  )
}
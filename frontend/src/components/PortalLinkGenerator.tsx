'use client'

import { useState, useEffect } from 'react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Copy, ExternalLink, QrCode, Share2, Check, Building, User } from 'lucide-react'

// API Configuration
const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE || 'http://localhost:8000'

interface PortalLinkGeneratorProps {
  workspaceId: string
}

interface PortalData {
  portal_url: string
  portal_slug: string
  workspace_id: string
  qr_code_url: string
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

  const copyToClipboard = async () => {
    if (!portalData?.portal_url) return

    try {
      await navigator.clipboard.writeText(portalData.portal_url)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    } catch (error) {
      console.error('Failed to copy to clipboard:', error)
      // Fallback for older browsers
      const textArea = document.createElement('textarea')
      textArea.value = portalData.portal_url
      document.body.appendChild(textArea)
      textArea.select()
      document.execCommand('copy')
      document.body.removeChild(textArea)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    }
  }

  const shareLink = async () => {
    if (!portalData?.portal_url) return

    if (navigator.share) {
      try {
        await navigator.share({
          title: 'Chat with our AI Assistant',
          text: 'Start a conversation with our AI assistant using this link:',
          url: portalData.portal_url,
        })
      } catch (error) {
        console.error('Error sharing:', error)
      }
    } else {
      // Fallback to copy
      copyToClipboard()
    }
  }

  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Portal Link</CardTitle>
          <CardDescription>Generate a link for your clients to access the chat</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex items-center justify-center py-8">
            <div className="w-6 h-6 border-2 border-blue-600 border-t-transparent rounded-full animate-spin mr-3"></div>
            <span className="text-gray-600">Generating portal link...</span>
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
          Portal Link
        </CardTitle>
        <CardDescription>
          Share this link with your clients to start conversations with your AI assistant
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
            {/* Portal Info */}
            <div className="bg-gradient-to-r from-blue-50 to-indigo-50 border border-blue-200 rounded-lg p-4 mb-4">
              <div className="flex items-center mb-2">
                {portalData.is_business_user ? (
                  <Building className="w-5 h-5 text-blue-600 mr-2" />
                ) : (
                  <User className="w-5 h-5 text-blue-600 mr-2" />
                )}
                <h4 className="text-sm font-medium text-blue-900">
                  {portalData.is_business_user ? 'Business Portal' : 'Personal Portal'}
                </h4>
              </div>
              <div className="text-sm text-blue-800 space-y-1">
                {portalData.is_business_user ? (
                  <>
                    <p><strong>Business:</strong> {portalData.user_info.business_name}</p>
                    <p><strong>Representative:</strong> {portalData.user_info.full_name}</p>
                  </>
                ) : (
                  <p><strong>Owner:</strong> {portalData.user_info.full_name}</p>
                )}
                <p><strong>Assistant:</strong> {portalData.user_info.assistant_name}</p>
                <p><strong>Custom URL:</strong> <code className="bg-blue-100 px-1 rounded">/portal/{portalData.portal_slug}</code></p>
              </div>
            </div>

            <div className="space-y-3">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Your Custom Portal Link
                </label>
                <div className="flex items-center space-x-2">
                  <input
                    type="text"
                    value={portalData.portal_url}
                    readOnly
                    className="flex-1 px-3 py-2 border border-gray-300 rounded-lg bg-gray-50 text-sm"
                  />
                  <Button
                    onClick={copyToClipboard}
                    variant="outline"
                    size="sm"
                    className="flex items-center"
                  >
                    {copied ? (
                      <>
                        <Check className="w-4 h-4 mr-1" />
                        Copied
                      </>
                    ) : (
                      <>
                        <Copy className="w-4 h-4 mr-1" />
                        Copy
                      </>
                    )}
                  </Button>
                </div>
                <p className="text-xs text-gray-500 mt-1">
                  This is your personalized, user-friendly portal URL that clients can easily remember and access.
                </p>
              </div>

              <div className="flex flex-wrap gap-2">
                <Button
                  onClick={() => window.open(portalData.portal_url, '_blank')}
                  variant="outline"
                  size="sm"
                  className="flex items-center"
                >
                  <ExternalLink className="w-4 h-4 mr-1" />
                  Test Link
                </Button>
                
                <Button
                  onClick={shareLink}
                  variant="outline"
                  size="sm"
                  className="flex items-center"
                >
                  <Share2 className="w-4 h-4 mr-1" />
                  Share
                </Button>

                <Button
                  onClick={() => window.open(portalData.qr_code_url, '_blank')}
                  variant="outline"
                  size="sm"
                  className="flex items-center"
                >
                  <QrCode className="w-4 h-4 mr-1" />
                  QR Code
                </Button>
              </div>
            </div>

            <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
              <h4 className="text-sm font-medium text-blue-900 mb-2">Instructions</h4>
              <p className="text-sm text-blue-800">{portalData.instructions}</p>
            </div>

            <div className="bg-gray-50 border border-gray-200 rounded-lg p-4">
              <h4 className="text-sm font-medium text-gray-900 mb-2">How it works</h4>
              <ul className="text-sm text-gray-700 space-y-1">
                <li>• <strong>User-friendly URL:</strong> Your portal has a custom, memorable URL based on your {portalData.is_business_user ? 'business and name' : 'name'}</li>
                <li>• <strong>No authentication required:</strong> Clients can access the portal directly without logging in</li>
                <li>• <strong>Phone verification:</strong> Clients enter their phone number to identify themselves</li>
                <li>• <strong>Instant chat:</strong> They can start chatting with your AI assistant immediately</li>
                <li>• <strong>Conversation history:</strong> All conversations are saved and accessible in your dashboard</li>
                <li>• <strong>Personalized AI:</strong> The AI uses your business knowledge and preferences</li>
              </ul>
            </div>
          </>
        )}

        {!portalData && !error && (
          <div className="text-center py-8">
            <p className="text-gray-600 mb-4">No portal link available</p>
            <Button onClick={generatePortalLink} variant="outline">
              Generate New Link
            </Button>
          </div>
        )}
      </CardContent>
    </Card>
  )
}

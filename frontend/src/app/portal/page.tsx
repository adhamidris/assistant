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
      const response = await fetch(`${API_BASE_URL}/api/v1/core/workspaces/${wsId}/`)
      if (response.ok) {
        const data = await response.json()
        setWorkspaceData(data)
      } else {
        setError('Workspace not found or access denied.')
      }
    } catch (error) {
      console.error('Failed to load workspace data:', error)
      setError('Failed to load workspace information.')
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

  return (
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
  )
}


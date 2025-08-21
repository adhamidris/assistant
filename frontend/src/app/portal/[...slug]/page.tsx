'use client'

import { useParams, useSearchParams } from 'next/navigation'
import { useState, useEffect, Suspense } from 'react'
import { Phone, MessageCircle, Bot } from 'lucide-react'
import { createSession, validateSession, getSessionToken, setSessionToken, setContactInfo } from '@/lib/api'
import { formatPhoneNumber, isValidPhoneNumber, toE164Format, getErrorMessage } from '@/lib/utils'
import ChatInterface from '@/components/ChatInterface'

// API Configuration
const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE || 'http://localhost:8000'

interface WorkspaceData {
  workspace_id: string
  workspace_name: string
  assistant_name: string
  portal_slug: string
}

function CustomPortalContent() {
  const params = useParams()
  const searchParams = useSearchParams()
  const [workspaceData, setWorkspaceData] = useState<WorkspaceData | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [step, setStep] = useState<'phone' | 'chat'>('phone')
  const [phoneNumber, setPhoneNumber] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [sessionData, setSessionData] = useState<any>(null)

  useEffect(() => {
    const resolvePortalSlug = async () => {
      try {
        // Get the slug path from the URL params
        const slugArray = params.slug as string[]
        const slugPath = slugArray.join('/')
        
        console.log('Resolving portal slug:', slugPath)
        
        // Call the backend API to resolve the slug
        const response = await fetch(`${API_BASE_URL}/api/v1/core/portal-resolve/${slugPath}/`)
        const data = await response.json()
        
        if (data.found) {
          setWorkspaceData(data)
          console.log('Portal resolved:', data)
        } else {
          setError('Portal not found. Please check the URL and try again.')
        }
      } catch (error) {
        console.error('Failed to resolve portal slug:', error)
        setError('Failed to load portal. Please try again later.')
      } finally {
        setLoading(false)
      }
    }

    if (params.slug) {
      resolvePortalSlug()
    }
    
    // Check for existing session on load
    checkExistingSession()
  }, [params.slug])

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

    if (!workspaceData) {
      setError('Portal not loaded. Please try again.')
      return
    }

    try {
      setIsLoading(true)
      const e164Phone = toE164Format(phoneNumber)
      
      const response = await createSession({
        phone_number: e164Phone,
        workspace_id: workspaceData.workspace_id
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

  if (loading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 flex items-center justify-center">
        <div className="bg-white rounded-lg shadow-lg p-8 max-w-md w-full mx-4">
          <div className="text-center">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
            <h2 className="text-xl font-semibold text-gray-900 mb-2">Loading Portal...</h2>
            <p className="text-gray-600">Please wait while we set up your chat experience.</p>
          </div>
        </div>
      </div>
    )
  }

  if (error && !workspaceData) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-red-50 to-pink-100 flex items-center justify-center">
        <div className="bg-white rounded-lg shadow-lg p-8 max-w-md w-full mx-4">
          <div className="text-center">
            <div className="w-16 h-16 bg-red-100 rounded-full flex items-center justify-center mx-auto mb-4">
              <svg className="w-8 h-8 text-red-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L3.732 16.5c-.77.833.192 2.5 1.732 2.5z" />
              </svg>
            </div>
            <h2 className="text-xl font-semibold text-gray-900 mb-2">Portal Not Found</h2>
            <p className="text-gray-600 mb-4">{error}</p>
            <button 
              onClick={() => window.location.href = '/'}
              className="bg-blue-600 text-white px-4 py-2 rounded-md hover:bg-blue-700 transition-colors"
            >
              Go to Homepage
            </button>
          </div>
        </div>
      </div>
    )
  }

  if (!workspaceData) {
    return null
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

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 flex items-center justify-center p-4">
      <div className="w-full max-w-md">
        {/* Header */}
        <div className="text-center mb-8">
          <div className="w-16 h-16 bg-gradient-to-br from-blue-500 to-indigo-600 rounded-full flex items-center justify-center mx-auto mb-4 shadow-lg">
            <Bot className="w-8 h-8 text-white" />
          </div>
          <h1 className="text-2xl font-bold text-gray-900 mb-2">
            {workspaceData.workspace_name}
          </h1>
          <p className="text-gray-600">
            Chat with {workspaceData.assistant_name}
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

export default function CustomPortalPage() {
  return (
    <Suspense fallback={
      <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    }>
      <CustomPortalContent />
    </Suspense>
  )
}

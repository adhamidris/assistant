import axios, { AxiosInstance, AxiosRequestConfig } from 'axios'

// API Configuration
const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE || 'http://localhost:8000'

// Create axios instance
const api: AxiosInstance = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
})

// Request interceptor to add auth token
api.interceptors.request.use(
  (config) => {
    const authToken = getAuthToken()
    console.log('API Interceptor: Auth token check:', !!authToken, authToken ? authToken.substring(0, 10) + '...' : 'none')
    console.log('API Interceptor: Request URL:', config.url)
    if (authToken) {
      config.headers.Authorization = `Token ${authToken}`
      console.log('API Interceptor: Added Authorization header')
    } else {
      console.log('API Interceptor: No auth token available')
    }
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

// Response interceptor for error handling
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      // Clear invalid session
      clearSession()
      // Don't automatically redirect - let components handle it
      console.log('API 401 error - session cleared')
    }
    return Promise.reject(error)
  }
)

// Auth token management (for APP users)
export const getAuthToken = (): string | null => {
  if (typeof window === 'undefined') return null
  const token = localStorage.getItem('authToken')
  console.log('getAuthToken: Retrieved token:', !!token, token ? token.substring(0, 10) + '...' : 'none')
  return token
}

export const setAuthToken = (token: string): void => {
  if (typeof window === 'undefined') return
  localStorage.setItem('authToken', token)
}

// Session management (for customer portal)
export const getSessionToken = (): string | null => {
  if (typeof window === 'undefined') return null
  const token = localStorage.getItem('session_token')
  console.log('getSessionToken: Retrieved token:', !!token, token ? token.substring(0, 10) + '...' : 'none')
  return token
}

export const setSessionToken = (token: string): void => {
  if (typeof window === 'undefined') return
  console.log('setSessionToken: Setting token:', token.substring(0, 10) + '...')
  localStorage.setItem('session_token', token)
}

export const clearSession = (): void => {
  if (typeof window === 'undefined') return
  localStorage.removeItem('session_token')
  localStorage.removeItem('contact_info')
  localStorage.removeItem('workspace_info')
}

export const getContactInfo = () => {
  if (typeof window === 'undefined') return null
  const info = localStorage.getItem('contact_info')
  return info ? JSON.parse(info) : null
}

export const setContactInfo = (info: any) => {
  if (typeof window === 'undefined') return
  localStorage.setItem('contact_info', JSON.stringify(info))
}

// API Types
export interface SessionCreateRequest {
  phone_number: string
  workspace_id: string
}

export interface SessionCreateResponse {
  session_token: string
  contact_id: string
  contact_name: string
  workspace_name: string
  assistant_name: string
  is_new_contact: boolean
}

export interface SessionValidateRequest {
  session_token: string
}

export interface SessionValidateResponse {
  valid: boolean
  contact_id: string
  contact_name: string
  workspace_name: string
  assistant_name: string
}

export interface Message {
  id: string
  conversation: string
  sender: 'client' | 'assistant' | 'owner'
  sender_display: string
  message_type: 'text' | 'audio' | 'file' | 'system'
  type_display: string
  status: 'sending' | 'sent' | 'processing' | 'processed' | 'failed'
  status_display: string
  text?: string
  media_url?: string
  media_filename?: string
  media_size?: number
  intent_classification?: string
  confidence_score?: number
  transcription?: {
    text: string
    language?: string
    confidence?: number
    duration?: number
  }
  created_at: string
  updated_at: string
}

export interface SendMessageRequest {
  text: string
  sender?: 'client' | 'owner'
}

export interface FileUploadRequest {
  file: File
  sender?: 'client' | 'owner'
}

export interface AudioUploadRequest {
  audio_file: File
  sender?: 'client' | 'owner'
}

export interface SearchKBRequest {
  query: string
  workspace_id?: string
  limit?: number
  threshold?: number
}

export interface KBChunk {
  id: string
  text: string
  chunk_index: number
  document_title: string
  document: string
  similarity_score: number
}

export interface SearchKBResponse {
  chunks: KBChunk[]
  query: string
  total_results: number
  search_time_ms: number
}

// API Functions

// Session Management
export const createSession = async (data: SessionCreateRequest): Promise<SessionCreateResponse> => {
  const response = await api.post('/api/v1/core/session/create/', data)
  return response.data
}

export const validateSession = async (data: SessionValidateRequest): Promise<SessionValidateResponse> => {
  const response = await api.post('/api/v1/core/session/validate/', data)
  return response.data
}

// Messaging (Authenticated Users)
export const getMessages = async (conversationId?: string): Promise<Message[]> => {
  const params = conversationId ? { conversation: conversationId } : {}
  
  // Debug authentication
  const authToken = getAuthToken()
  console.log('getMessages: Auth token check:', !!authToken, authToken ? authToken.substring(0, 10) + '...' : 'none')
  
  const response = await api.get('/api/v1/messaging/messages/', { params })
  return response.data.results || response.data
}

export const sendMessage = async (data: SendMessageRequest): Promise<Message> => {
  const response = await api.post('/api/v1/messaging/messages/', data)
  return response.data
}

// Session-based Messaging (Portal Clients)
export const getSessionMessages = async (conversationId?: string): Promise<Message[]> => {
  const sessionToken = getSessionToken()
  console.log('getSessionMessages: Session token check:', !!sessionToken, sessionToken ? sessionToken.substring(0, 10) + '...' : 'none')
  
  if (!sessionToken) {
    console.warn('No session token available for getSessionMessages')
    return []
  }
  
  let url = `${API_BASE_URL}/api/v1/messaging/session-messages/`
  if (conversationId) {
    url += `?conversation=${conversationId}`
  }
  
  console.log('getSessionMessages: Making request to', url)
  console.log('getSessionMessages: API_BASE_URL:', API_BASE_URL)
  
  try {
    console.log('getSessionMessages: About to make fetch request...')
    const response = await fetch(url, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
        'X-Session-Token': sessionToken,
      }
    })
    
    console.log('getSessionMessages: Response received, status:', response.status)
    console.log('getSessionMessages: Response headers:', Object.fromEntries(response.headers.entries()))
    
    if (!response.ok) {
      console.error('Session messages API error:', response.status, response.statusText)
      const errorText = await response.text()
      console.error('Error response body:', errorText)
      return []
    }
    
    const data = await response.json()
    console.log('getSessionMessages: Success, got', data.results?.length || data.length, 'messages')
    return data.results || data
  } catch (error) {
    console.error('Failed to fetch session messages:', error)
    console.error('Error details:', {
      name: error.name,
      message: error.message,
      stack: error.stack
    })
    return []
  }
}

export const sendSessionMessage = async (data: SendMessageRequest): Promise<Message> => {
  const sessionToken = getSessionToken()
  if (!sessionToken) {
    throw new Error('No session token available')
  }
  
  try {
    const response = await fetch(`${API_BASE_URL}/api/v1/messaging/session-messages/`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-Session-Token': sessionToken,
      },
      body: JSON.stringify(data)
    })
    
    if (!response.ok) {
      const errorText = await response.text()
      throw new Error(`Failed to send message: ${response.status} ${errorText}`)
    }
    
    return response.json()
  } catch (error) {
    console.error('Failed to send session message:', error)
    throw error
  }
}

export const uploadFile = async (data: FileUploadRequest): Promise<Message> => {
  const formData = new FormData()
  formData.append('file', data.file)
  formData.append('sender', data.sender || 'client')

  const response = await api.post('/api/v1/messaging/upload-file/', formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
  })
  return response.data
}

export const uploadAudio = async (data: AudioUploadRequest): Promise<Message> => {
  const formData = new FormData()
  formData.append('audio_file', data.audio_file)
  formData.append('sender', data.sender || 'client')

  const response = await api.post('/api/v1/messaging/upload-audio/', formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
  })
  return response.data
}

// Knowledge Base
export const searchKnowledgeBase = async (data: SearchKBRequest): Promise<SearchKBResponse> => {
  const response = await api.post('/api/v1/knowledge-base/search/', data)
  return response.data
}

// Admin API functions (for owner dashboard)
export const getConversations = async (workspaceId?: string) => {
  const params = workspaceId ? { workspace: workspaceId } : {}
  const response = await api.get('/api/v1/core/conversations/', { params })
  return response.data
}

export const getContacts = async (workspaceId?: string) => {
  const params = workspaceId ? { workspace: workspaceId } : {}
  const response = await api.get('/api/v1/core/contacts/', { params })
  return response.data
}

export const getDrafts = async (conversationId?: string) => {
  const params = conversationId ? { conversation: conversationId, pending: 'true' } : { pending: 'true' }
  const response = await api.get('/api/v1/messaging/drafts/', { params })
  return response.data
}

export const approveDraft = async (draftId: string, action: 'approve' | 'reject', modifiedText?: string) => {
  const response = await api.post('/api/v1/messaging/approve-draft/', {
    draft_id: draftId,
    action,
    modified_text: modifiedText,
  })
  return response.data
}

// Message Details API Functions
export const getMessageDetails = async (messageId: string): Promise<Message> => {
  const response = await api.get(`/api/v1/messaging/messages/${messageId}/details/`)
  return response.data
}

export const updateMessageStatus = async (messageId: string, status: string): Promise<Message> => {
  const response = await api.put(`/api/v1/messaging/messages/${messageId}/status/`, { status })
  return response.data
}

export const replyToMessage = async (messageId: string, text: string): Promise<Message> => {
  const response = await api.post(`/api/v1/messaging/messages/${messageId}/reply/`, { text })
  return response.data
}

export const deleteMessage = async (messageId: string): Promise<void> => {
  await api.delete(`/api/v1/messaging/messages/${messageId}/`)
}

export default api


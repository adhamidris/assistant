'use client'

import { useState, useEffect, useRef } from 'react'
import { Send, Paperclip, Mic, MicOff, Bot, User, FileText, Volume2, X } from 'lucide-react'
import { getMessages, sendMessage, getSessionMessages, sendSessionMessage, uploadFile, uploadAudio, getSessionToken, startTypingIndicator, stopTypingIndicator, type Message } from '@/lib/api'
import { formatMessageTime, formatFileSize, getMessageIcon, getStatusIcon, getErrorMessage } from '@/lib/utils'

interface ChatInterfaceProps {
  sessionData?: {
    contact_id: string
    contact_name: string
    workspace_name: string
    assistant_name: string
    agent_id?: string
    agent_slug?: string
  }
  selectedAgent?: {
    id: string
    name: string
    slug: string
    description: string
    channel_type: string
    generated_prompt: string
    business_context: any
    personality_config: any
  }
}

export default function ChatInterface({ sessionData, selectedAgent }: ChatInterfaceProps) {
  const [messages, setMessages] = useState<Message[]>([])
  const [newMessage, setNewMessage] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [isRecording, setIsRecording] = useState(false)
  const [isTyping, setIsTyping] = useState(false)
  const [error, setError] = useState('')

  // Early return if sessionData is provided but no session token exists
  if (sessionData && (!getSessionToken() || !sessionData.contact_id || !sessionData.workspace_name)) {
    console.error('ChatInterface: Invalid sessionData or missing session token', { sessionData, hasToken: !!getSessionToken() })
    return (
      <div className="h-screen flex items-center justify-center bg-gradient-to-br from-red-50 to-pink-100">
        <div className="text-center max-w-md mx-auto p-6">
          <div className="w-16 h-16 bg-red-100 rounded-full flex items-center justify-center mx-auto mb-4">
            <Bot className="w-8 h-8 text-red-600" />
          </div>
          <h2 className="text-xl font-semibold text-gray-900 mb-2">Session Error</h2>
          <p className="text-gray-600 mb-4">There was an issue with your session. Please refresh the page and try again.</p>
          <button 
            onClick={() => window.location.reload()}
            className="bg-blue-600 text-white px-4 py-2 rounded-md hover:bg-blue-700 transition-colors"
          >
            Refresh Page
          </button>
        </div>
      </div>
    )
  }
  
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)
  const mediaRecorderRef = useRef<MediaRecorder | null>(null)
  const audioChunksRef = useRef<Blob[]>([])

  useEffect(() => {
    loadMessages()
    // Poll for new messages every 3 seconds
    const interval = setInterval(loadMessages, 3000)
    return () => clearInterval(interval)
  }, [])

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  const loadMessages = async () => {
    try {
      // Use session-based API if sessionData is available (portal clients)
      // Otherwise use authenticated API (dashboard users)
      if (sessionData && sessionData.contact_id && sessionData.workspace_name) {
        // Double-check that we have a session token before making the call
        const sessionToken = getSessionToken()
        if (!sessionToken) {
          console.warn('ChatInterface: sessionData exists but no session token found')
          return // Don't try to load messages without a session token
        }
        const fetchedMessages = await getSessionMessages()
        setMessages(fetchedMessages)
      } else {
        // Only try authenticated API if we're not in a portal context
        const fetchedMessages = await getMessages()
        setMessages(fetchedMessages)
      }
    } catch (error) {
      console.error('Failed to load messages:', error)
      // Don't set error state for initial load failures
    }
  }

  const handleSendMessage = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!newMessage.trim() || isLoading) return

    const messageText = newMessage.trim()
    setNewMessage('')
    setError('')
    setIsLoading(true)
    setIsTyping(true)
    
    // Start typing indicator with agent name
    try {
      if (sessionData?.contact_id) {
        await startTypingIndicator(sessionData.contact_id, selectedAgent?.name)
      }
    } catch (error) {
      console.warn('Failed to start typing indicator:', error)
    }

    try {
      // Use session-based API if sessionData is available (portal clients)
      // Otherwise use authenticated API (dashboard users)
      if (sessionData && sessionData.contact_id && sessionData.workspace_name) {
        // Double-check that we have a session token before sending
        const sessionToken = getSessionToken()
        if (!sessionToken) {
          throw new Error('No session token available. Please refresh the page and try again.')
        }
        // Include agent context if available
        const messageData: any = { text: messageText }
        if (selectedAgent?.id) {
          messageData.agent_id = selectedAgent.id
          messageData.agent_context = {
            name: selectedAgent.name,
            slug: selectedAgent.slug,
            channel_type: selectedAgent.channel_type,
            generated_prompt: selectedAgent.generated_prompt,
            business_context: selectedAgent.business_context,
            personality_config: selectedAgent.personality_config
          }
        }
        await sendSessionMessage(messageData)
      } else {
        await sendMessage({ text: messageText })
      }
      
      // Load messages immediately to show user message
      await loadMessages()
      
      // Keep checking for AI response
      let attempts = 0
      const maxAttempts = 10
      const checkForResponse = async () => {
        attempts++
        await loadMessages()
        
        // Check if we got a new assistant message
        let latestMessages: Message[] = []
        try {
          if (sessionData && sessionData.contact_id && sessionData.workspace_name) {
            const sessionToken = getSessionToken()
            if (sessionToken) {
              latestMessages = await getSessionMessages()
            }
          } else {
            latestMessages = await getMessages()
          }
        } catch (error) {
          console.error('Failed to check for new messages:', error)
        }
        
        const hasNewAssistantMessage = latestMessages.some(msg => 
          msg.sender === 'assistant' && 
          new Date(msg.created_at).getTime() > new Date().getTime() - 10000 // Within last 10 seconds
        )
        
        if (hasNewAssistantMessage || attempts >= maxAttempts) {
          setIsTyping(false)
          // Stop typing indicator
          try {
            if (sessionData?.contact_id) {
              await stopTypingIndicator(sessionData.contact_id)
            }
          } catch (error) {
            console.warn('Failed to stop typing indicator:', error)
          }
        } else {
          // Check again in 1 second
          setTimeout(checkForResponse, 1000)
        }
      }
      
      // Start checking for AI response after a short delay
      setTimeout(checkForResponse, 1000)
      
    } catch (error) {
      setError(getErrorMessage(error))
      setIsTyping(false)
      // Stop typing indicator on error
      try {
        if (sessionData?.contact_id) {
          await stopTypingIndicator(sessionData.contact_id)
        }
      } catch (stopError) {
        console.warn('Failed to stop typing indicator on error:', stopError)
      }
    } finally {
      setIsLoading(false)
    }
  }

  const handleFileUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0]
    if (!file) return

    setIsLoading(true)
    setError('')

    try {
      await uploadFile({ file })
      await loadMessages()
    } catch (error) {
      setError(getErrorMessage(error))
    } finally {
      setIsLoading(false)
      if (fileInputRef.current) {
        fileInputRef.current.value = ''
      }
    }
  }

  const startRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      const mediaRecorder = new MediaRecorder(stream)
      
      mediaRecorderRef.current = mediaRecorder
      audioChunksRef.current = []

      mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          audioChunksRef.current.push(event.data)
        }
      }

      mediaRecorder.onstop = async () => {
        const audioBlob = new Blob(audioChunksRef.current, { type: 'audio/wav' })
        const audioFile = new File([audioBlob], 'recording.wav', { type: 'audio/wav' })
        
        setIsLoading(true)
        try {
          await uploadAudio({ audio_file: audioFile })
          await loadMessages()
        } catch (error) {
          setError(getErrorMessage(error))
        } finally {
          setIsLoading(false)
        }

        // Stop all tracks
        stream.getTracks().forEach(track => track.stop())
      }

      mediaRecorder.start()
      setIsRecording(true)
    } catch (error) {
      setError('Microphone access denied or not available')
    }
  }

  const stopRecording = () => {
    if (mediaRecorderRef.current && isRecording) {
      mediaRecorderRef.current.stop()
      setIsRecording(false)
    }
  }

  const clearError = () => setError('')

  return (
    <div className="h-screen flex flex-col bg-gradient-to-br from-blue-50 to-indigo-100">
      {/* Header */}
      <div className="bg-white/80 backdrop-blur-sm border-b border-gray-200/50 px-4 py-4 shadow-sm">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <div className="w-12 h-12 bg-gradient-to-br from-blue-500 to-indigo-600 rounded-full flex items-center justify-center shadow-lg">
              <Bot className="w-7 h-7 text-white" />
            </div>
            <div>
              <h1 className="text-lg font-semibold text-gray-900">
                {selectedAgent?.name || sessionData?.assistant_name || 'AI Assistant'}
              </h1>
              <p className="text-sm text-gray-500 flex items-center">
                <span className="w-2 h-2 bg-green-500 rounded-full mr-2 animate-pulse"></span>
                {sessionData?.workspace_name || 'Demo Business'} Support
                {selectedAgent && (
                  <span className="ml-2 px-2 py-1 bg-blue-100 text-blue-800 text-xs rounded-full">
                    {selectedAgent.channel_type}
                  </span>
                )}
              </p>
              {selectedAgent?.description && (
                <p className="text-xs text-gray-400 mt-1">
                  {selectedAgent.description}
                </p>
              )}
            </div>
          </div>
          <div className="flex items-center space-x-2">
            <span className="inline-flex items-center px-3 py-1 rounded-full text-xs font-medium bg-green-100 text-green-800 shadow-sm">
              <span className="w-1.5 h-1.5 bg-green-500 rounded-full mr-1.5"></span>
              Online
            </span>
          </div>
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4 space-y-6 scrollbar-thin">
        {messages.length === 0 ? (
          <div className="text-center py-12">
            <div className="w-16 h-16 bg-gradient-to-br from-blue-500 to-indigo-600 rounded-full flex items-center justify-center mx-auto mb-6 shadow-lg">
              <Bot className="w-8 h-8 text-white" />
            </div>
                         <h3 className="text-lg font-semibold text-gray-900 mb-2">
               Welcome to {sessionData?.workspace_name || 'Demo Business'}!
             </h3>
             <p className="text-gray-600 max-w-md mx-auto">
               Hi {sessionData?.contact_name || 'there'}! I'm {selectedAgent?.name || 'your AI assistant'}. 
               {selectedAgent?.description ? ` ${selectedAgent.description}` : ' How can I help you today?'}
             </p>
            <div className="mt-6 flex flex-wrap gap-2 justify-center">
              <button 
                onClick={() => setNewMessage("I have a question about your services")}
                className="px-4 py-2 bg-white/80 backdrop-blur-sm rounded-full text-sm text-gray-700 hover:bg-white/90 transition-colors shadow-sm border border-gray-200/50"
              >
                Ask about services
              </button>
              <button 
                onClick={() => setNewMessage("I'd like to book an appointment")}
                className="px-4 py-2 bg-white/80 backdrop-blur-sm rounded-full text-sm text-gray-700 hover:bg-white/90 transition-colors shadow-sm border border-gray-200/50"
              >
                Book appointment
              </button>
              <button 
                onClick={() => setNewMessage("I need help with something")}
                className="px-4 py-2 bg-white/80 backdrop-blur-sm rounded-full text-sm text-gray-700 hover:bg-white/90 transition-colors shadow-sm border border-gray-200/50"
              >
                Get help
              </button>
            </div>
          </div>
        ) : (
          messages.map((message) => (
            <MessageBubble key={message.id} message={message} />
          ))
        )}

        {isTyping && (
          <div className="flex items-start space-x-3 animate-fade-in">
            <div className="w-10 h-10 bg-gradient-to-br from-blue-500 to-indigo-600 rounded-full flex items-center justify-center shadow-lg">
              <Bot className="w-5 h-5 text-white" />
            </div>
            <div className="bg-white/90 backdrop-blur-sm rounded-2xl rounded-bl-md px-4 py-3 shadow-lg border border-gray-200/50 max-w-xs">
              <div className="flex items-center space-x-2">
                <span className="text-sm text-gray-600 font-medium">
                  {selectedAgent?.name || 'AI Assistant'} is typing
                </span>
                <div className="typing-indicator">
                  <div className="typing-dot bg-blue-500"></div>
                  <div className="typing-dot bg-blue-500"></div>
                  <div className="typing-dot bg-blue-500"></div>
                </div>
              </div>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Error Banner */}
      {error && (
        <div className="bg-red-50 border-l-4 border-red-400 p-4 mx-4">
          <div className="flex justify-between">
            <div className="flex">
              <div className="ml-3">
                <p className="text-sm text-red-700">{error}</p>
              </div>
            </div>
            <button
              onClick={clearError}
              className="text-red-400 hover:text-red-600"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        </div>
      )}

      {/* Message Input */}
      <div className="bg-white/80 backdrop-blur-sm border-t border-gray-200/50 p-4 shadow-lg">
        <form onSubmit={handleSendMessage} className="flex items-end space-x-3">
          <div className="flex-1">
            <div className="relative">
              <textarea
                value={newMessage}
                onChange={(e) => setNewMessage(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault()
                    handleSendMessage(e)
                  }
                }}
                placeholder="Type your message..."
                className="w-full px-4 py-3 pr-12 border border-gray-300/50 rounded-2xl bg-white/90 backdrop-blur-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 resize-none transition-all duration-200 shadow-sm text-gray-900 placeholder-gray-500"
                rows={1}
                style={{ minHeight: '48px', maxHeight: '120px' }}
              />
              <div className="absolute right-3 top-1/2 transform -translate-y-1/2">
                <button
                  type="button"
                  onClick={() => fileInputRef.current?.click()}
                  disabled={isLoading}
                  className="p-1.5 text-gray-400 hover:text-blue-500 rounded-lg transition-colors hover:bg-blue-50"
                  title="Attach file"
                >
                  <Paperclip className="w-4 h-4" />
                </button>
              </div>
            </div>
          </div>

          {/* Voice Recording */}
          <button
            type="button"
            onClick={isRecording ? stopRecording : startRecording}
            disabled={isLoading}
            className={`p-3 rounded-2xl transition-all duration-200 shadow-lg hover:shadow-xl transform hover:scale-105 ${
              isRecording 
                ? 'bg-gradient-to-br from-red-500 to-red-600 text-white animate-pulse' 
                : 'bg-white/90 backdrop-blur-sm text-gray-600 hover:text-red-500 border border-gray-200/50'
            } disabled:opacity-50 disabled:scale-100`}
            title={isRecording ? "Stop recording" : "Start voice message"}
          >
            {isRecording ? <MicOff className="w-5 h-5" /> : <Mic className="w-5 h-5" />}
          </button>

          {/* Send Button */}
          <button
            type="submit"
            disabled={!newMessage.trim() || isLoading}
            className="bg-gradient-to-br from-blue-500 to-indigo-600 hover:from-blue-600 hover:to-indigo-700 disabled:from-gray-300 disabled:to-gray-400 disabled:cursor-not-allowed text-white p-3 rounded-2xl transition-all duration-200 shadow-lg hover:shadow-xl disabled:shadow-none transform hover:scale-105 disabled:scale-100"
            title="Send message"
          >
            {isLoading ? (
              <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin" />
            ) : (
              <Send className="w-5 h-5" />
            )}
          </button>

          <input
            type="file"
            ref={fileInputRef}
            onChange={handleFileUpload}
            accept=".pdf,.doc,.docx,.txt,.jpg,.jpeg,.png"
            className="hidden"
          />
        </form>
      </div>
    </div>
  )
}

function MessageBubble({ message }: { message: Message }) {
  const isClient = message.sender === 'client'

  return (
    <div className={`flex items-start space-x-3 ${isClient ? 'flex-row-reverse space-x-reverse' : ''} animate-fade-in`}>
      <div className={`w-10 h-10 rounded-full flex items-center justify-center shadow-lg ${
        isClient 
          ? 'bg-gradient-to-br from-blue-500 to-indigo-600' 
          : 'bg-gradient-to-br from-gray-400 to-gray-500'
      }`}>
        {isClient ? (
          <User className="w-5 h-5 text-white" />
        ) : (
          <Bot className="w-5 h-5 text-white" />
        )}
      </div>
      
      <div className={`max-w-xs lg:max-w-md ${isClient ? 'ml-auto' : 'mr-auto'}`}>
        <div className={`px-4 py-3 rounded-2xl shadow-lg border border-gray-200/50 ${
          isClient 
            ? 'bg-gradient-to-br from-blue-500 to-indigo-600 text-white rounded-br-md' 
            : 'bg-white/90 backdrop-blur-sm text-gray-900 rounded-bl-md'
        }`}>
          {message.message_type === 'text' && (
            <p className="text-sm leading-relaxed">{message.text}</p>
          )}
          
          {message.message_type === 'audio' && (
            <div className="space-y-2">
              <div className="flex items-center space-x-2">
                <Volume2 className="w-4 h-4" />
                <span className="text-sm">Audio message</span>
              </div>
              {message.transcription && (
                <div className="pt-2 border-t border-opacity-20">
                  <p className="text-xs opacity-75">{message.transcription.text}</p>
                </div>
              )}
            </div>
          )}
          
          {message.message_type === 'file' && (
            <div className="flex items-center space-x-3">
              <div className="w-10 h-10 bg-gray-100 rounded-lg flex items-center justify-center">
                <FileText className="w-5 h-5 text-gray-600" />
              </div>
              <div>
                <p className="text-sm font-medium">{message.media_filename}</p>
                {message.media_size && (
                  <p className="text-xs opacity-75">{formatFileSize(message.media_size)}</p>
                )}
              </div>
            </div>
          )}
        </div>
        
        <div className={`flex items-center mt-2 space-x-2 text-xs text-gray-500 ${
          isClient ? 'justify-end' : 'justify-start'
        }`}>
          <span>{formatMessageTime(message.created_at)}</span>
          <span>{getStatusIcon(message.status)}</span>
        </div>
        
        {message.intent_classification && !isClient && (
          <div className="mt-2">
            <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-blue-100 text-blue-800 shadow-sm">
              {message.intent_classification}
            </span>
          </div>
        )}
      </div>
    </div>
  )
}


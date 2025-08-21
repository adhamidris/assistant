'use client'

import { useState, useEffect } from 'react'
import { MessageSquare, User, Clock, CheckCircle, AlertCircle, Eye } from 'lucide-react'
import { getConversations, getMessages, deleteMessage, replyToMessage } from '@/lib/api'
import { formatRelativeTime, getIntentColor, getIntentLabel } from '@/lib/utils'
import MessageDetails from './MessageDetails'

interface ConversationListProps {
  workspaceId: string
}

interface Conversation {
  id: string
  contact: {
    id: string
    name: string
    masked_phone: string
  }
  status: 'active' | 'resolved' | 'archived'
  last_intent: string
  message_count: number
  created_at: string
  updated_at: string
}

export default function ConversationList({ workspaceId }: ConversationListProps) {
  const [conversations, setConversations] = useState<Conversation[]>([])
  const [selectedConversation, setSelectedConversation] = useState<string | null>(null)
  const [messages, setMessages] = useState<any[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [filter, setFilter] = useState<'all' | 'active' | 'resolved'>('all')
  const [selectedMessage, setSelectedMessage] = useState<any>(null)
  const [showMessageDetails, setShowMessageDetails] = useState(false)

  useEffect(() => {
    loadConversations()
  }, [workspaceId, filter])

  const loadConversations = async () => {
    try {
      setIsLoading(true)
      const data = await getConversations(workspaceId)
      
      let filteredData = data.results || data
      if (filter !== 'all') {
        filteredData = filteredData.filter((c: Conversation) => c.status === filter)
      }
      
      setConversations(filteredData)
    } catch (error) {
      console.error('Failed to load conversations:', error)
      setConversations([])
    } finally {
      setIsLoading(false)
    }
  }

  const loadConversationMessages = async (conversationId: string) => {
    try {
      const conversationMessages = await getMessages(conversationId)
      setMessages(conversationMessages)
      setSelectedConversation(conversationId)
    } catch (error) {
      console.error('Failed to load messages:', error)
      setMessages([])
    }
  }

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'active':
        return <AlertCircle className="w-4 h-4 text-yellow-500" />
      case 'resolved':
        return <CheckCircle className="w-4 h-4 text-green-500" />
      default:
        return <Clock className="w-4 h-4 text-gray-400" />
    }
  }

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'active':
        return 'bg-yellow-100 text-yellow-800'
      case 'resolved':
        return 'bg-green-100 text-green-800'
      case 'archived':
        return 'bg-gray-100 text-gray-800'
      default:
        return 'bg-gray-100 text-gray-800'
    }
  }

  const handleMessageClick = (message: any) => {
    setSelectedMessage(message)
    setShowMessageDetails(true)
  }

  const handleMessageDelete = async (messageId: string) => {
    try {
      await deleteMessage(messageId)
      // Reload messages after deletion
      if (selectedConversation) {
        await loadConversationMessages(selectedConversation)
      }
    } catch (error) {
      console.error('Failed to delete message:', error)
    }
  }

  const handleMessageReply = async (messageId: string) => {
    // This could open a reply modal or focus the input field
    console.log('Reply to message:', messageId)
    setShowMessageDetails(false)
    // You could implement a reply modal here
  }

  if (isLoading) {
    return (
      <div className="text-center py-8">
        <div className="w-6 h-6 border-2 border-blue-600 border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
        <p className="text-gray-600">Loading conversations...</p>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h3 className="text-lg font-semibold text-gray-900">Conversations</h3>
        
        {/* Filter Buttons */}
        <div className="flex space-x-2">
          {['all', 'active', 'resolved'].map((filterOption) => (
            <button
              key={filterOption}
              onClick={() => setFilter(filterOption as any)}
              className={`px-3 py-1 text-sm rounded-full capitalize ${
                filter === filterOption
                  ? 'bg-blue-100 text-blue-800'
                  : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
              }`}
            >
              {filterOption}
            </button>
          ))}
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Conversations List */}
        <div className="space-y-3">
          {conversations.length === 0 ? (
            <div className="text-center py-8">
              <MessageSquare className="w-12 h-12 text-gray-400 mx-auto mb-4" />
              <p className="text-gray-500">No conversations found</p>
            </div>
          ) : (
            conversations.map((conversation) => (
              <div
                key={conversation.id}
                onClick={() => loadConversationMessages(conversation.id)}
                className={`p-4 border rounded-lg cursor-pointer transition-colors ${
                  selectedConversation === conversation.id
                    ? 'border-blue-500 bg-blue-50'
                    : 'border-gray-200 hover:border-gray-300 hover:bg-gray-50'
                }`}
              >
                <div className="flex items-start justify-between">
                  <div className="flex items-start space-x-3">
                    <div className="w-10 h-10 bg-gray-100 rounded-full flex items-center justify-center">
                      <User className="w-5 h-5 text-gray-600" />
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center space-x-2">
                        <p className="text-sm font-medium text-gray-900 truncate">
                          {conversation.contact.name || 'Unknown Contact'}
                        </p>
                        {getStatusIcon(conversation.status)}
                      </div>
                      <p className="text-xs text-gray-500">
                        {conversation.contact.masked_phone}
                      </p>
                      <div className="flex items-center space-x-2 mt-1">
                        <span className={`inline-flex items-center px-2 py-1 rounded text-xs font-medium ${getIntentColor(conversation.last_intent)}`}>
                          {getIntentLabel(conversation.last_intent)}
                        </span>
                        <span className={`inline-flex items-center px-2 py-1 rounded text-xs font-medium ${getStatusColor(conversation.status)}`}>
                          {conversation.status}
                        </span>
                      </div>
                    </div>
                  </div>
                  <div className="text-right">
                    <p className="text-xs text-gray-500">
                      {formatRelativeTime(conversation.updated_at)}
                    </p>
                    <p className="text-xs text-gray-400 mt-1">
                      {conversation.message_count} messages
                    </p>
                  </div>
                </div>
              </div>
            ))
          )}
        </div>

        {/* Messages Preview */}
        <div className="border border-gray-200 rounded-lg">
          {selectedConversation ? (
            <div className="h-96 overflow-y-auto p-4 space-y-3">
              <h4 className="font-medium text-gray-900 sticky top-0 bg-white pb-2">
                Conversation Messages
              </h4>
              {messages.length === 0 ? (
                <p className="text-gray-500 text-center py-8">No messages found</p>
              ) : (
                messages.map((message) => (
                  <div
                    key={message.id}
                    className={`flex ${
                      message.sender === 'client' ? 'justify-end' : 'justify-start'
                    }`}
                  >
                    <div
                      className={`max-w-xs px-3 py-2 rounded-lg text-sm cursor-pointer hover:shadow-md transition-shadow ${
                        message.sender === 'client'
                          ? 'bg-blue-500 text-white'
                          : message.sender === 'assistant'
                          ? 'bg-gray-100 text-gray-900'
                          : 'bg-green-100 text-green-900'
                      }`}
                      onClick={() => handleMessageClick(message)}
                    >
                      <div className="flex items-center justify-between">
                        <p className="flex-1">{message.text || `[${message.message_type}]`}</p>
                        <Eye className="w-3 h-3 opacity-50 hover:opacity-100 transition-opacity" />
                      </div>
                      <p className={`text-xs mt-1 ${
                        message.sender === 'client' ? 'text-blue-100' : 'text-gray-500'
                      }`}>
                        {formatRelativeTime(message.created_at)}
                      </p>
                    </div>
                  </div>
                ))
              )}
            </div>
          ) : (
            <div className="h-96 flex items-center justify-center text-gray-500">
              <div className="text-center">
                <MessageSquare className="w-12 h-12 mx-auto mb-4 text-gray-400" />
                <p>Select a conversation to view messages</p>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Message Details Modal */}
      <MessageDetails
        message={selectedMessage}
        isOpen={showMessageDetails}
        onClose={() => setShowMessageDetails(false)}
        onReply={handleMessageReply}
        onDelete={handleMessageDelete}
      />
    </div>
  )
}


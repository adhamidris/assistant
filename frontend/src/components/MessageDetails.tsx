'use client'

import { useState, useEffect } from 'react'
import { 
  X, 
  Clock, 
  User, 
  Bot, 
  FileText, 
  Volume2, 
  Download, 
  Copy, 
  Trash2, 
  Edit3,
  MessageSquare,
  AlertCircle,
  CheckCircle,
  Loader2,
  Calendar,
  Tag,
  BarChart3,
  Sparkles
} from 'lucide-react'
import { Message } from '@/lib/api'
import { formatMessageTime, formatFileSize } from '@/lib/utils'

interface MessageDetailsProps {
  message: Message | null
  isOpen: boolean
  onClose: () => void
  onReply?: (messageId: string) => void
  onDelete?: (messageId: string) => void
  onStatusUpdate?: (messageId: string, status: string) => void
}

export default function MessageDetails({
  message,
  isOpen,
  onClose,
  onReply,
  onDelete,
  onStatusUpdate
}: MessageDetailsProps) {
  const [isLoading, setIsLoading] = useState(false)
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false)
  const [copySuccess, setCopySuccess] = useState(false)
  const [downloadLoading, setDownloadLoading] = useState(false)
  const [replyLoading, setReplyLoading] = useState(false)

  // Keyboard support
  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape' && isOpen) {
        onClose()
      }
    }

    if (isOpen) {
      document.addEventListener('keydown', handleKeyDown)
      return () => document.removeEventListener('keydown', handleKeyDown)
    }
  }, [isOpen, onClose])

  if (!isOpen || !message) return null

  const getSenderIcon = (sender: string) => {
    switch (sender) {
      case 'client':
        return <User className="w-5 h-5 text-blue-600" />
      case 'assistant':
        return <Bot className="w-5 h-5 text-green-600" />
      case 'owner':
        return <MessageSquare className="w-5 h-5 text-purple-600" />
      default:
        return <User className="w-5 h-5 text-gray-600" />
    }
  }

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'sent':
        return 'text-green-600 bg-green-50'
      case 'sending':
        return 'text-yellow-600 bg-yellow-50'
      case 'processing':
        return 'text-blue-600 bg-blue-50'
      case 'failed':
        return 'text-red-600 bg-red-50'
      default:
        return 'text-gray-600 bg-gray-50'
    }
  }

  const getMessageTypeIcon = (type: string) => {
    switch (type) {
      case 'text':
        return <MessageSquare className="w-4 h-4" />
      case 'audio':
        return <Volume2 className="w-4 h-4" />
      case 'file':
        return <FileText className="w-4 h-4" />
      default:
        return <MessageSquare className="w-4 h-4" />
    }
  }

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'sending':
        return <Clock className="w-3 h-3" />
      case 'sent':
        return <CheckCircle className="w-3 h-3" />
      case 'processing':
        return <Loader2 className="w-3 h-3 animate-spin" />
      case 'processed':
        return <CheckCircle className="w-3 h-3" />
      case 'failed':
        return <AlertCircle className="w-3 h-3" />
      default:
        return <Clock className="w-3 h-3" />
    }
  }

  const handleCopyText = async () => {
    if (message.text) {
      try {
        await navigator.clipboard.writeText(message.text)
        setCopySuccess(true)
        setTimeout(() => setCopySuccess(false), 2000)
      } catch (error) {
        console.error('Failed to copy text:', error)
      }
    }
  }

  const handleDownloadFile = async () => {
    if (message.media_url) {
      setDownloadLoading(true)
      try {
        const link = document.createElement('a')
        link.href = message.media_url
        link.download = message.media_filename || 'download'
        link.click()
        // Simulate a small delay for better UX
        await new Promise(resolve => setTimeout(resolve, 500))
      } catch (error) {
        console.error('Failed to download file:', error)
      } finally {
        setDownloadLoading(false)
      }
    }
  }

  const handleDelete = async () => {
    if (!onDelete) return
    
    setIsLoading(true)
    try {
      await onDelete(message.id)
      setShowDeleteConfirm(false)
      onClose()
    } catch (error) {
      console.error('Failed to delete message:', error)
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-50 p-4 animate-in fade-in duration-300" role="dialog" aria-modal="true" aria-labelledby="message-details-title">
      <div className="bg-white/95 backdrop-blur-md rounded-2xl shadow-2xl max-w-3xl w-full max-h-[90vh] overflow-hidden border border-white/20 animate-in slide-in-from-bottom-4 duration-300">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-gray-100 bg-gradient-to-r from-gray-50 to-white">
          <div className="flex items-center space-x-4">
            <div className="p-2 bg-gradient-to-br from-blue-500 to-indigo-600 rounded-xl shadow-lg">
              {getSenderIcon(message.sender)}
            </div>
            <div>
              <h2 id="message-details-title" className="text-xl font-bold bg-gradient-to-r from-gray-900 to-gray-700 bg-clip-text text-transparent">
                Message Details
              </h2>
              <p className="text-sm text-gray-600 font-medium">
                {message.sender_display} • {formatMessageTime(message.created_at)}
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-2 text-gray-400 hover:text-gray-600 hover:bg-gray-100 rounded-xl transition-all duration-200 group focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2"
            title="Close (Esc)"
          >
            <X className="w-6 h-6" />
            <span className="absolute -bottom-8 left-1/2 transform -translate-x-1/2 bg-gray-900 text-white text-xs px-2 py-1 rounded opacity-0 group-hover:opacity-100 group-focus:opacity-100 transition-opacity duration-200 pointer-events-none">
              Esc
            </span>
          </button>
        </div>

                {/* Content */}
        <div className="overflow-y-auto max-h-[calc(90vh-200px)] scrollbar-thin scrollbar-thumb-gray-300 scrollbar-track-gray-100">
          {/* Message Content */}
          <div className="p-6 border-b border-gray-100">
            <div className="flex items-start space-x-4">
              <div className="flex-shrink-0">
                <div className="p-2 bg-gradient-to-br from-blue-50 to-indigo-50 rounded-xl">
                  {getSenderIcon(message.sender)}
                </div>
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex items-center space-x-3 mb-3">
                  <span className="font-semibold text-gray-900">
                    {message.sender_display}
                  </span>
                  <span className="text-sm text-gray-500 font-medium">
                    {formatMessageTime(message.created_at)}
                  </span>
                  <span className={`inline-flex items-center px-3 py-1 rounded-full text-xs font-semibold ${getStatusColor(message.status)} shadow-sm`}>
                    {getStatusIcon(message.status)}
                    <span className="ml-1">{message.status_display}</span>
                  </span>
                </div>

                {/* Message Content */}
                <div className="bg-gradient-to-br from-gray-50 to-blue-50 rounded-xl p-5 mb-4 border border-gray-100 shadow-sm">
                  {message.message_type === 'text' && (
                    <div className="bg-white rounded-xl p-4 border border-gray-100 shadow-sm">
                      <p className="text-gray-900 whitespace-pre-wrap leading-relaxed text-base">{message.text}</p>
                    </div>
                  )}
                  
                  {message.message_type === 'audio' && (
                    <div className="space-y-4">
                      <div className="flex items-center space-x-3">
                        <div className="p-2 bg-gradient-to-br from-blue-500 to-indigo-600 rounded-xl">
                          <Volume2 className="w-5 h-5 text-white" />
                        </div>
                        <span className="font-semibold text-gray-900">Audio Message</span>
                      </div>
                      {message.media_url && (
                        <div className="bg-white rounded-xl p-4 border border-gray-100 shadow-sm">
                          <audio controls className="w-full">
                            <source src={message.media_url} type="audio/wav" />
                            Your browser does not support the audio element.
                          </audio>
                        </div>
                      )}
                      {message.transcription && (
                        <div className="mt-4 p-4 bg-gradient-to-r from-blue-50 to-indigo-50 rounded-xl border border-blue-100">
                          <div className="flex items-center space-x-2 mb-2">
                            <FileText className="w-4 h-4 text-blue-600" />
                            <p className="text-sm font-semibold text-blue-700">Transcription</p>
                          </div>
                          <p className="text-sm text-gray-800 leading-relaxed">{message.transcription.text}</p>
                          {message.transcription.confidence && (
                            <div className="mt-2 flex items-center space-x-2">
                              <div className="w-2 h-2 bg-blue-500 rounded-full"></div>
                              <p className="text-xs text-blue-600 font-medium">
                                Confidence: {Math.round(message.transcription.confidence * 100)}%
                              </p>
                            </div>
                          )}
                        </div>
                      )}
                    </div>
                  )}
                  
                  {message.message_type === 'file' && (
                    <div className="space-y-4">
                      <div className="flex items-center space-x-4">
                        <div className="p-3 bg-gradient-to-br from-blue-500 to-indigo-600 rounded-xl shadow-lg">
                          <FileText className="w-8 h-8 text-white" />
                        </div>
                        <div>
                          <p className="font-semibold text-gray-900 text-lg">{message.media_filename}</p>
                          {message.media_size && (
                            <p className="text-sm text-gray-600 font-medium">
                              {formatFileSize(message.media_size)}
                            </p>
                          )}
                        </div>
                      </div>
                      {message.media_url && (
                        <button
                          onClick={handleDownloadFile}
                          disabled={downloadLoading}
                          className="inline-flex items-center space-x-3 px-4 py-3 bg-gradient-to-r from-blue-600 to-indigo-600 text-white rounded-xl hover:from-blue-700 hover:to-indigo-700 transition-all duration-200 shadow-lg hover:shadow-xl transform hover:scale-105 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed"
                        >
                          {downloadLoading ? (
                            <>
                              <Loader2 className="w-4 h-4 animate-spin" />
                              <span className="font-medium">Downloading...</span>
                            </>
                          ) : (
                            <>
                              <Download className="w-4 h-4" />
                              <span className="font-medium">Download File</span>
                            </>
                          )}
                        </button>
                      )}
                    </div>
                  )}
                </div>

                {/* AI Analysis */}
                {message.intent_classification && (
                  <div className="flex items-center space-x-3 mb-4 p-3 bg-gradient-to-r from-purple-50 to-indigo-50 rounded-xl border border-purple-100">
                    <div className="p-1.5 bg-gradient-to-br from-purple-500 to-indigo-600 rounded-lg">
                      <Sparkles className="w-4 h-4 text-white" />
                    </div>
                    <div className="flex items-center space-x-2">
                      <span className="text-sm font-semibold text-purple-700">AI Analysis</span>
                      <span className="inline-flex items-center px-3 py-1 rounded-full text-xs font-semibold bg-purple-100 text-purple-800 shadow-sm">
                        {message.intent_classification}
                      </span>
                      {message.confidence_score && (
                        <span className="text-xs text-purple-600 font-medium">
                          ({Math.round(message.confidence_score * 100)}% confidence)
                        </span>
                      )}
                    </div>
                  </div>
                )}
                          </div>
          </div>
        </div>

          {/* Message Metadata */}
          <div className="p-6 border-b border-gray-100 bg-gradient-to-r from-gray-50 to-white">
            <div className="flex items-center space-x-2 mb-4">
              <div className="p-1.5 bg-gradient-to-br from-blue-500 to-indigo-600 rounded-lg">
                <FileText className="w-4 h-4 text-white" />
              </div>
              <h3 className="text-lg font-semibold text-gray-900">Message Information</h3>
            </div>
                        <div className="grid grid-cols-2 gap-6 text-sm">
              <div className="p-3 bg-white rounded-xl border border-gray-100 shadow-sm hover:shadow-md transition-all duration-200 hover:border-gray-200">
                <span className="text-gray-500 font-medium text-xs uppercase tracking-wide">Message ID</span>
                <p className="font-mono text-gray-900 font-semibold mt-1">{message.id}</p>
              </div>
              <div className="p-3 bg-white rounded-xl border border-gray-100 shadow-sm hover:shadow-md transition-all duration-200 hover:border-gray-200">
                <span className="text-gray-500 font-medium text-xs uppercase tracking-wide">Type</span>
                <div className="flex items-center space-x-2 mt-1">
                  {getMessageTypeIcon(message.message_type)}
                  <span className="text-gray-900 font-semibold">{message.type_display}</span>
                </div>
              </div>
              <div className="p-3 bg-white rounded-xl border border-gray-100 shadow-sm hover:shadow-md transition-all duration-200 hover:border-gray-200">
                <span className="text-gray-500 font-medium text-xs uppercase tracking-wide">Created</span>
                <p className="text-gray-900 font-semibold mt-1">{formatMessageTime(message.created_at)}</p>
              </div>
              <div className="p-3 bg-white rounded-xl border border-gray-100 shadow-sm hover:shadow-md transition-all duration-200 hover:border-gray-200">
                <span className="text-gray-500 font-medium text-xs uppercase tracking-wide">Updated</span>
                <p className="text-gray-900 font-semibold mt-1">{formatMessageTime(message.updated_at)}</p>
              </div>
              <div className="p-3 bg-white rounded-xl border border-gray-100 shadow-sm hover:shadow-md transition-all duration-200 hover:border-gray-200">
                <span className="text-gray-500 font-medium text-xs uppercase tracking-wide">Status</span>
                <div className="flex items-center space-x-2 mt-1">
                  {getStatusIcon(message.status)}
                  <span className="text-gray-900 font-semibold">{message.status_display}</span>
                </div>
              </div>
              <div className="p-3 bg-white rounded-xl border border-gray-100 shadow-sm hover:shadow-md transition-all duration-200 hover:border-gray-200">
                <span className="text-gray-500 font-medium text-xs uppercase tracking-wide">Sender</span>
                <p className="text-gray-900 font-semibold mt-1">{message.sender_display}</p>
              </div>
            </div>
          </div>

                    {/* Actions */}
          <div className="p-6 bg-gradient-to-r from-gray-50 to-white">
            <div className="flex items-center space-x-2 mb-4">
              <div className="p-1.5 bg-gradient-to-br from-green-500 to-emerald-600 rounded-lg">
                <MessageSquare className="w-4 h-4 text-white" />
              </div>
              <h3 className="text-lg font-semibold text-gray-900">Actions</h3>
            </div>
            <div className="flex flex-wrap gap-4">
              {message.text && (
                <button
                  onClick={handleCopyText}
                  className={`inline-flex items-center space-x-3 px-4 py-3 rounded-xl transition-all duration-200 border shadow-sm hover:shadow-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 ${
                    copySuccess 
                      ? 'bg-green-50 text-green-700 border-green-200' 
                      : 'bg-white text-gray-700 hover:bg-gray-50 border-gray-200'
                  }`}
                >
                  {copySuccess ? (
                    <>
                      <CheckCircle className="w-4 h-4" />
                      <span className="font-medium">Copied!</span>
                    </>
                  ) : (
                    <>
                      <Copy className="w-4 h-4" />
                      <span className="font-medium">Copy Text</span>
                    </>
                  )}
                </button>
              )}

              {onReply && (
                <button
                  onClick={() => {
                    setReplyLoading(true)
                    onReply(message.id)
                    setTimeout(() => setReplyLoading(false), 1000)
                  }}
                  disabled={replyLoading}
                  className="inline-flex items-center space-x-3 px-4 py-3 bg-gradient-to-r from-blue-600 to-indigo-600 text-white rounded-xl hover:from-blue-700 hover:to-indigo-700 transition-all duration-200 shadow-lg hover:shadow-xl transform hover:scale-105 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {replyLoading ? (
                    <>
                      <Loader2 className="w-4 h-4 animate-spin" />
                      <span className="font-medium">Opening...</span>
                    </>
                  ) : (
                    <>
                      <MessageSquare className="w-4 h-4" />
                      <span className="font-medium">Reply</span>
                    </>
                  )}
                </button>
              )}

              {onDelete && (
                <button
                  onClick={() => setShowDeleteConfirm(true)}
                  className="inline-flex items-center space-x-3 px-4 py-3 bg-gradient-to-r from-red-600 to-pink-600 text-white rounded-xl hover:from-red-700 hover:to-pink-700 transition-all duration-200 shadow-lg hover:shadow-xl transform hover:scale-105 focus:outline-none focus:ring-2 focus:ring-red-500 focus:ring-offset-2"
                >
                  <Trash2 className="w-4 h-4" />
                  <span className="font-medium">Delete</span>
                </button>
              )}
            </div>
          </div>
        </div>

        {/* Delete Confirmation Modal */}
        {showDeleteConfirm && (
          <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-60 animate-in fade-in duration-200">
            <div className="bg-white/95 backdrop-blur-md rounded-2xl p-6 max-w-md w-full mx-4 shadow-2xl border border-white/20 animate-in slide-in-from-bottom-4 duration-200">
              <div className="flex items-center space-x-3 mb-4">
                <div className="p-2 bg-gradient-to-br from-red-500 to-pink-600 rounded-xl">
                  <AlertCircle className="w-6 h-6 text-white" />
                </div>
                <h3 className="text-xl font-bold text-gray-900">Delete Message</h3>
              </div>
              <p className="text-gray-600 mb-6 leading-relaxed">
                Are you sure you want to delete this message? This action cannot be undone.
              </p>
              <div className="flex justify-end space-x-3">
                <button
                  onClick={() => setShowDeleteConfirm(false)}
                  className="px-6 py-3 text-gray-700 bg-gray-100 rounded-xl hover:bg-gray-200 transition-all duration-200 font-medium focus:outline-none focus:ring-2 focus:ring-gray-500 focus:ring-offset-2"
                  disabled={isLoading}
                >
                  Cancel
                </button>
                <button
                  onClick={handleDelete}
                  className="px-6 py-3 bg-gradient-to-r from-red-600 to-pink-600 text-white rounded-xl hover:from-red-700 hover:to-pink-700 transition-all duration-200 disabled:opacity-50 shadow-lg hover:shadow-xl transform hover:scale-105 font-medium focus:outline-none focus:ring-2 focus:ring-red-500 focus:ring-offset-2"
                  disabled={isLoading}
                >
                  {isLoading ? (
                    <div className="flex items-center space-x-2">
                      <Loader2 className="w-4 h-4 animate-spin" />
                      <span>Deleting...</span>
                    </div>
                  ) : (
                    <div className="flex items-center space-x-2">
                      <Trash2 className="w-4 h-4" />
                      <span>Delete</span>
                    </div>
                  )}
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

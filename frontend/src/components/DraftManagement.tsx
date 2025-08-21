'use client'

import { useState, useEffect } from 'react'
import { Clock, Check, X, Edit3, MessageSquare } from 'lucide-react'
import { getDrafts, approveDraft } from '@/lib/api'
import { formatRelativeTime, getErrorMessage } from '@/lib/utils'

interface Draft {
  id: string
  conversation_id: string
  suggested_text: string
  confidence_score?: number
  context_sources: string[]
  is_approved: boolean
  is_rejected: boolean
  created_at: string
}

export default function DraftManagement() {
  const [drafts, setDrafts] = useState<Draft[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [processingDraft, setProcessingDraft] = useState<string | null>(null)
  const [editingDraft, setEditingDraft] = useState<string | null>(null)
  const [editText, setEditText] = useState('')
  const [error, setError] = useState('')

  useEffect(() => {
    loadDrafts()
  }, [])

  const loadDrafts = async () => {
    try {
      setIsLoading(true)
      const data = await getDrafts()
      setDrafts(data.results || data)
    } catch (error) {
      console.error('Failed to load drafts:', error)
      setDrafts([])
    } finally {
      setIsLoading(false)
    }
  }

  const handleApproveDraft = async (draftId: string, action: 'approve' | 'reject', modifiedText?: string) => {
    try {
      setProcessingDraft(draftId)
      setError('')
      
      await approveDraft(draftId, action, modifiedText)
      await loadDrafts() // Refresh the list
      
      if (editingDraft === draftId) {
        setEditingDraft(null)
        setEditText('')
      }
    } catch (error) {
      setError(getErrorMessage(error))
    } finally {
      setProcessingDraft(null)
    }
  }

  const startEditing = (draft: Draft) => {
    setEditingDraft(draft.id)
    setEditText(draft.suggested_text)
  }

  const cancelEditing = () => {
    setEditingDraft(null)
    setEditText('')
  }

  const saveAndApprove = async (draftId: string) => {
    await handleApproveDraft(draftId, 'approve', editText)
  }

  if (isLoading) {
    return (
      <div className="text-center py-8">
        <div className="w-6 h-6 border-2 border-blue-600 border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
        <p className="text-gray-600">Loading drafts...</p>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h3 className="text-lg font-semibold text-gray-900">Draft Messages</h3>
        <span className="text-sm text-gray-500">
          {drafts.length} pending approval{drafts.length !== 1 ? 's' : ''}
        </span>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4">
          <p className="text-sm text-red-600">{error}</p>
        </div>
      )}

      {drafts.length === 0 ? (
        <div className="text-center py-12">
          <MessageSquare className="w-12 h-12 text-gray-400 mx-auto mb-4" />
          <p className="text-gray-500">No pending drafts</p>
          <p className="text-sm text-gray-400 mt-1">
            All AI responses are being sent automatically
          </p>
        </div>
      ) : (
        <div className="space-y-4">
          {drafts.map((draft) => (
            <div key={draft.id} className="bg-white border border-gray-200 rounded-lg p-6">
              <div className="flex items-start justify-between mb-4">
                <div className="flex items-center space-x-2">
                  <Clock className="w-4 h-4 text-yellow-500" />
                  <span className="text-sm font-medium text-gray-900">
                    Draft Response
                  </span>
                  {draft.confidence_score && (
                    <span className="text-xs text-gray-500">
                      {Math.round(draft.confidence_score * 100)}% confidence
                    </span>
                  )}
                </div>
                <span className="text-xs text-gray-500">
                  {formatRelativeTime(draft.created_at)}
                </span>
              </div>

              {/* Draft Content */}
              <div className="mb-4">
                {editingDraft === draft.id ? (
                  <textarea
                    value={editText}
                    onChange={(e) => setEditText(e.target.value)}
                    className="w-full p-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                    rows={4}
                    placeholder="Edit the response..."
                  />
                ) : (
                  <div className="bg-gray-50 rounded-lg p-4">
                    <p className="text-sm text-gray-900 whitespace-pre-wrap">
                      {draft.suggested_text}
                    </p>
                  </div>
                )}
              </div>

              {/* Context Sources */}
              {draft.context_sources.length > 0 && (
                <div className="mb-4">
                  <p className="text-xs text-gray-600 mb-2">
                    Based on {draft.context_sources.length} knowledge base source{draft.context_sources.length !== 1 ? 's' : ''}
                  </p>
                </div>
              )}

              {/* Actions */}
              <div className="flex items-center justify-between">
                <div className="flex space-x-2">
                  {editingDraft === draft.id ? (
                    <>
                      <button
                        onClick={() => saveAndApprove(draft.id)}
                        disabled={processingDraft === draft.id}
                        className="flex items-center px-3 py-1.5 bg-blue-600 text-white text-sm rounded-lg hover:bg-blue-700 disabled:opacity-50"
                      >
                        <Check className="w-4 h-4 mr-1" />
                        Save & Approve
                      </button>
                      <button
                        onClick={cancelEditing}
                        disabled={processingDraft === draft.id}
                        className="flex items-center px-3 py-1.5 bg-gray-200 text-gray-700 text-sm rounded-lg hover:bg-gray-300"
                      >
                        Cancel
                      </button>
                    </>
                  ) : (
                    <>
                      <button
                        onClick={() => handleApproveDraft(draft.id, 'approve')}
                        disabled={processingDraft === draft.id}
                        className="flex items-center px-3 py-1.5 bg-green-600 text-white text-sm rounded-lg hover:bg-green-700 disabled:opacity-50"
                      >
                        {processingDraft === draft.id ? (
                          <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin mr-1"></div>
                        ) : (
                          <Check className="w-4 h-4 mr-1" />
                        )}
                        Approve
                      </button>
                      <button
                        onClick={() => startEditing(draft)}
                        disabled={processingDraft === draft.id}
                        className="flex items-center px-3 py-1.5 bg-blue-600 text-white text-sm rounded-lg hover:bg-blue-700 disabled:opacity-50"
                      >
                        <Edit3 className="w-4 h-4 mr-1" />
                        Edit
                      </button>
                      <button
                        onClick={() => handleApproveDraft(draft.id, 'reject')}
                        disabled={processingDraft === draft.id}
                        className="flex items-center px-3 py-1.5 bg-red-600 text-white text-sm rounded-lg hover:bg-red-700 disabled:opacity-50"
                      >
                        <X className="w-4 h-4 mr-1" />
                        Reject
                      </button>
                    </>
                  )}
                </div>
                
                <button className="text-xs text-gray-500 hover:text-gray-700">
                  View Conversation
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}


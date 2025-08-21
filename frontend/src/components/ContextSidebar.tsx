'use client'

import React, { useState, useEffect } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Badge } from '@/components/ui/badge'
import { AlertCircle, CheckCircle, Clock, Edit2, Save, X, Bot, User } from 'lucide-react'

interface ContextField {
  id: string
  label: string
  type: string
  value?: any
  confidence?: number
  required?: boolean
  choices?: string[]
}

interface ConversationContext {
  id: string
  title: string
  status: string
  priority: string
  completion_percentage: number
  context_data: Record<string, any>
  ai_confidence_scores: Record<string, number>
  tags: string[]
  schema: {
    id: string
    name: string
    fields: ContextField[]
  }
  last_ai_update?: string
  last_human_update?: string
}

interface ContextSidebarProps {
  conversationId: string
  workspaceId: string
  onContextUpdate?: (context: ConversationContext) => void
}

export default function ContextSidebar({ conversationId, workspaceId, onContextUpdate }: ContextSidebarProps) {
  const [context, setContext] = useState<ConversationContext | null>(null)
  const [loading, setLoading] = useState(true)
  const [editing, setEditing] = useState(false)
  const [editedValues, setEditedValues] = useState<Record<string, any>>({})
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    fetchContext()
  }, [conversationId])

  const fetchContext = async () => {
    try {
      setLoading(true)
      const response = await fetch(`/api/v1/context/conversations/${conversationId}/contexts/`)
      if (response.ok) {
        const data = await response.json()
        if (data.length > 0) {
          setContext(data[0]) // Get the first context
        }
      }
    } catch (error) {
      console.error('Failed to fetch context:', error)
    } finally {
      setLoading(false)
    }
  }

  const handleSave = async () => {
    if (!context) return

    try {
      setSaving(true)
      const response = await fetch(`/api/v1/context/conversations/${conversationId}/contexts/${context.id}/update-fields/`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          field_updates: editedValues,
        }),
      })

      if (response.ok) {
        const updatedContext = await response.json()
        setContext(updatedContext)
        setEditedValues({})
        setEditing(false)
        onContextUpdate?.(updatedContext)
      }
    } catch (error) {
      console.error('Failed to save context:', error)
    } finally {
      setSaving(false)
    }
  }

  const handleStatusChange = async (newStatus: string) => {
    if (!context) return

    try {
      const response = await fetch(`/api/v1/context/conversations/${conversationId}/contexts/${context.id}/change-status/`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ status: newStatus }),
      })

      if (response.ok) {
        const updatedContext = await response.json()
        setContext(updatedContext)
        onContextUpdate?.(updatedContext)
      }
    } catch (error) {
      console.error('Failed to change status:', error)
    }
  }

  const getFieldValue = (field: ContextField) => {
    if (editing && editedValues.hasOwnProperty(field.id)) {
      return editedValues[field.id]
    }
    return context?.context_data[field.id] || ''
  }

  const getConfidenceColor = (confidence: number) => {
    if (confidence >= 0.8) return 'text-green-600'
    if (confidence >= 0.6) return 'text-yellow-600'
    return 'text-red-600'
  }

  const getPriorityColor = (priority: string) => {
    switch (priority) {
      case 'urgent': return 'bg-red-100 text-red-800'
      case 'high': return 'bg-orange-100 text-orange-800'
      case 'medium': return 'bg-blue-100 text-blue-800'
      case 'low': return 'bg-gray-100 text-gray-800'
      default: return 'bg-gray-100 text-gray-800'
    }
  }

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'new': return 'bg-blue-100 text-blue-800'
      case 'in_progress': return 'bg-yellow-100 text-yellow-800'
      case 'resolved': return 'bg-green-100 text-green-800'
      case 'closed': return 'bg-gray-100 text-gray-800'
      default: return 'bg-gray-100 text-gray-800'
    }
  }

  const renderField = (field: ContextField) => {
    const value = getFieldValue(field)
    const confidence = context?.ai_confidence_scores[field.id]

    if (!editing) {
      return (
        <div key={field.id} className="space-y-1">
          <div className="flex items-center justify-between">
            <label className="text-sm font-medium text-gray-700">
              {field.label}
              {field.required && <span className="text-red-500 ml-1">*</span>}
            </label>
            {confidence !== undefined && (
              <div className="flex items-center space-x-1">
                <Bot className="h-3 w-3" />
                <span className={`text-xs ${getConfidenceColor(confidence)}`}>
                  {(confidence * 100).toFixed(0)}%
                </span>
              </div>
            )}
          </div>
          <div className="text-sm text-gray-900 bg-gray-50 p-2 rounded border">
            {value || <span className="text-gray-400">Not set</span>}
          </div>
        </div>
      )
    }

    // Editing mode
    if (field.type === 'choice' || field.type === 'status') {
      return (
        <div key={field.id} className="space-y-1">
          <label className="text-sm font-medium text-gray-700">
            {field.label}
            {field.required && <span className="text-red-500 ml-1">*</span>}
          </label>
          <Select
            value={value}
            onValueChange={(newValue) => 
              setEditedValues({ ...editedValues, [field.id]: newValue })
            }
          >
            <SelectTrigger>
              <SelectValue placeholder="Select..." />
            </SelectTrigger>
            <SelectContent>
              {field.choices?.map((choice) => (
                <SelectItem key={choice} value={choice}>
                  {choice}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      )
    }

    if (field.type === 'textarea') {
      return (
        <div key={field.id} className="space-y-1">
          <label className="text-sm font-medium text-gray-700">
            {field.label}
            {field.required && <span className="text-red-500 ml-1">*</span>}
          </label>
          <Textarea
            value={value}
            onChange={(e) => 
              setEditedValues({ ...editedValues, [field.id]: e.target.value })
            }
            placeholder={`Enter ${field.label.toLowerCase()}...`}
          />
        </div>
      )
    }

    return (
      <div key={field.id} className="space-y-1">
        <label className="text-sm font-medium text-gray-700">
          {field.label}
          {field.required && <span className="text-red-500 ml-1">*</span>}
        </label>
        <Input
          value={value}
          onChange={(e) => 
            setEditedValues({ ...editedValues, [field.id]: e.target.value })
          }
          placeholder={`Enter ${field.label.toLowerCase()}...`}
        />
      </div>
    )
  }

  if (loading) {
    return (
      <div className="w-80 border-l bg-white p-4">
        <div className="animate-pulse space-y-4">
          <div className="h-4 bg-gray-200 rounded w-3/4"></div>
          <div className="h-4 bg-gray-200 rounded w-1/2"></div>
          <div className="h-20 bg-gray-200 rounded"></div>
        </div>
      </div>
    )
  }

  if (!context) {
    return (
      <div className="w-80 border-l bg-white p-4">
        <Card>
          <CardContent className="pt-6">
            <div className="text-center text-gray-500">
              <AlertCircle className="h-8 w-8 mx-auto mb-2" />
              <p>No context available for this conversation.</p>
            </div>
          </CardContent>
        </Card>
      </div>
    )
  }

  return (
    <div className="w-80 border-l bg-white flex flex-col h-full">
      <div className="p-4 border-b">
        <div className="flex items-center justify-between mb-3">
          <h3 className="font-semibold text-gray-900">Conversation Context</h3>
          {!editing ? (
            <Button
              variant="outline"
              size="sm"
              onClick={() => setEditing(true)}
            >
              <Edit2 className="h-4 w-4" />
            </Button>
          ) : (
            <div className="flex space-x-1">
              <Button
                variant="outline"
                size="sm"
                onClick={() => {
                  setEditing(false)
                  setEditedValues({})
                }}
              >
                <X className="h-4 w-4" />
              </Button>
              <Button
                variant="default"
                size="sm"
                onClick={handleSave}
                disabled={saving}
              >
                <Save className="h-4 w-4" />
              </Button>
            </div>
          )}
        </div>

        {/* Status and Priority */}
        <div className="flex space-x-2 mb-3">
          <Badge className={getStatusColor(context.status)}>
            {context.status}
          </Badge>
          <Badge className={getPriorityColor(context.priority)}>
            {context.priority}
          </Badge>
        </div>

        {/* Completion Progress */}
        <div className="mb-3">
          <div className="flex items-center justify-between text-sm">
            <span className="text-gray-600">Completion</span>
            <span className="font-medium">{context.completion_percentage}%</span>
          </div>
          <div className="w-full bg-gray-200 rounded-full h-2">
            <div
              className="bg-blue-600 h-2 rounded-full transition-all duration-300"
              style={{ width: `${context.completion_percentage}%` }}
            ></div>
          </div>
        </div>

        {/* Schema Info */}
        <div className="text-sm text-gray-600 mb-3">
          <strong>Schema:</strong> {context.schema.name}
        </div>
      </div>

      {/* Context Fields */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {context.schema.fields.map(renderField)}

        {/* Tags */}
        {context.tags.length > 0 && (
          <div className="space-y-2">
            <label className="text-sm font-medium text-gray-700">Tags</label>
            <div className="flex flex-wrap gap-1">
              {context.tags.map((tag, index) => (
                <Badge key={index} variant="secondary" className="text-xs">
                  {tag}
                </Badge>
              ))}
            </div>
          </div>
        )}

        {/* Last Updates */}
        <div className="pt-4 border-t text-xs text-gray-500 space-y-1">
          {context.last_ai_update && (
            <div className="flex items-center space-x-1">
              <Bot className="h-3 w-3" />
              <span>AI updated: {new Date(context.last_ai_update).toLocaleString()}</span>
            </div>
          )}
          {context.last_human_update && (
            <div className="flex items-center space-x-1">
              <User className="h-3 w-3" />
              <span>Human updated: {new Date(context.last_human_update).toLocaleString()}</span>
            </div>
          )}
        </div>
      </div>

      {/* Quick Actions */}
      <div className="p-4 border-t space-y-2">
        <div className="text-sm font-medium text-gray-700 mb-2">Quick Status Change</div>
        <div className="grid grid-cols-2 gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() => handleStatusChange('in_progress')}
            disabled={context.status === 'in_progress'}
          >
            <Clock className="h-4 w-4 mr-1" />
            In Progress
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={() => handleStatusChange('resolved')}
            disabled={context.status === 'resolved'}
          >
            <CheckCircle className="h-4 w-4 mr-1" />
            Resolved
          </Button>
        </div>
      </div>
    </div>
  )
}

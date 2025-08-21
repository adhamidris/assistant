'use client'

import React, { useState } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Badge } from '@/components/ui/badge'
import { Switch } from '@/components/ui/switch'
import { Plus, Trash2, Move, Settings } from 'lucide-react'

interface FieldDefinition {
  id: string
  label: string
  type: string
  required: boolean
  ai_extractable: boolean
  choices?: string[]
  help_text?: string
  display_order: number
}

interface SchemaBuilderProps {
  workspaceId: string
  initialSchema?: any
  onSave?: (schema: any) => void
  onCancel?: () => void
}

const FIELD_TYPES = [
  { value: 'text', label: 'Text Field' },
  { value: 'textarea', label: 'Text Area' },
  { value: 'choice', label: 'Choice Dropdown' },
  { value: 'multi_choice', label: 'Multi-Select' },
  { value: 'date', label: 'Date' },
  { value: 'datetime', label: 'Date & Time' },
  { value: 'number', label: 'Number' },
  { value: 'boolean', label: 'Yes/No' },
  { value: 'email', label: 'Email' },
  { value: 'phone', label: 'Phone Number' },
  { value: 'tags', label: 'Tags' },
]

const DEFAULT_STATUSES = [
  { id: 'new', label: 'New', color: 'blue' },
  { id: 'in_progress', label: 'In Progress', color: 'yellow' },
  { id: 'resolved', label: 'Resolved', color: 'green' },
  { id: 'closed', label: 'Closed', color: 'gray' },
]

export default function SchemaBuilder({ workspaceId, initialSchema, onSave, onCancel }: SchemaBuilderProps) {
  const [schema, setSchema] = useState({
    name: initialSchema?.name || '',
    description: initialSchema?.description || '',
    is_default: initialSchema?.is_default || false,
    fields: initialSchema?.fields || [],
    status_workflow: initialSchema?.status_workflow || {
      statuses: DEFAULT_STATUSES,
      transitions: {}
    }
  })

  const [saving, setSaving] = useState(false)

  const addField = () => {
    const newField: FieldDefinition = {
      id: `field_${Date.now()}`,
      label: 'New Field',
      type: 'text',
      required: false,
      ai_extractable: true,
      display_order: schema.fields.length + 1
    }
    setSchema({
      ...schema,
      fields: [...schema.fields, newField]
    })
  }

  const updateField = (index: number, updates: Partial<FieldDefinition>) => {
    const updatedFields = [...schema.fields]
    updatedFields[index] = { ...updatedFields[index], ...updates }
    setSchema({ ...schema, fields: updatedFields })
  }

  const removeField = (index: number) => {
    const updatedFields = schema.fields.filter((_, i) => i !== index)
    setSchema({ ...schema, fields: updatedFields })
  }

  const moveField = (index: number, direction: 'up' | 'down') => {
    const newIndex = direction === 'up' ? index - 1 : index + 1
    if (newIndex < 0 || newIndex >= schema.fields.length) return

    const updatedFields = [...schema.fields]
    const [field] = updatedFields.splice(index, 1)
    updatedFields.splice(newIndex, 0, field)
    
    // Update display orders
    updatedFields.forEach((field, i) => {
      field.display_order = i + 1
    })

    setSchema({ ...schema, fields: updatedFields })
  }

  const handleSave = async () => {
    if (!schema.name.trim()) {
      alert('Schema name is required')
      return
    }

    setSaving(true)
    try {
      const endpoint = initialSchema?.id 
        ? `/api/v1/context/workspaces/${workspaceId}/schemas/${initialSchema.id}/`
        : `/api/v1/context/workspaces/${workspaceId}/schemas/`
      
      const method = initialSchema?.id ? 'PUT' : 'POST'

      const response = await fetch(endpoint, {
        method,
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(schema),
      })

      if (response.ok) {
        const savedSchema = await response.json()
        onSave?.(savedSchema)
      } else {
        throw new Error('Failed to save schema')
      }
    } catch (error) {
      console.error('Error saving schema:', error)
      alert('Failed to save schema')
    } finally {
      setSaving(false)
    }
  }

  const renderFieldEditor = (field: FieldDefinition, index: number) => (
    <Card key={field.id} className="mb-4">
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <CardTitle className="text-sm">Field {index + 1}</CardTitle>
          <div className="flex space-x-1">
            <Button
              variant="outline"
              size="sm"
              onClick={() => moveField(index, 'up')}
              disabled={index === 0}
            >
              ↑
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={() => moveField(index, 'down')}
              disabled={index === schema.fields.length - 1}
            >
              ↓
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={() => removeField(index)}
            >
              <Trash2 className="h-4 w-4" />
            </Button>
          </div>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="text-sm font-medium">Field ID</label>
            <Input
              value={field.id}
              onChange={(e) => updateField(index, { id: e.target.value })}
              placeholder="field_id"
            />
          </div>
          <div>
            <label className="text-sm font-medium">Label</label>
            <Input
              value={field.label}
              onChange={(e) => updateField(index, { label: e.target.value })}
              placeholder="Field Label"
            />
          </div>
        </div>

        <div>
          <label className="text-sm font-medium">Field Type</label>
          <Select
            value={field.type}
            onValueChange={(value) => updateField(index, { type: value })}
          >
            <SelectTrigger>
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {FIELD_TYPES.map((type) => (
                <SelectItem key={type.value} value={type.value}>
                  {type.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        {(field.type === 'choice' || field.type === 'multi_choice') && (
          <div>
            <label className="text-sm font-medium">Choices (one per line)</label>
            <Textarea
              value={field.choices?.join('\n') || ''}
              onChange={(e) => updateField(index, { 
                choices: e.target.value.split('\n').filter(c => c.trim()) 
              })}
              placeholder="option1&#10;option2&#10;option3"
            />
          </div>
        )}

        <div>
          <label className="text-sm font-medium">Help Text</label>
          <Input
            value={field.help_text || ''}
            onChange={(e) => updateField(index, { help_text: e.target.value })}
            placeholder="Optional help text for users"
          />
        </div>

        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <Switch
              checked={field.required}
              onCheckedChange={(checked) => updateField(index, { required: checked })}
            />
            <label className="text-sm">Required</label>
          </div>
          <div className="flex items-center space-x-2">
            <Switch
              checked={field.ai_extractable}
              onCheckedChange={(checked) => updateField(index, { ai_extractable: checked })}
            />
            <label className="text-sm">AI Extractable</label>
          </div>
        </div>
      </CardContent>
    </Card>
  )

  return (
    <div className="max-w-4xl mx-auto p-6 space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">
          {initialSchema ? 'Edit Schema' : 'Create Schema'}
        </h1>
        <div className="flex space-x-2">
          <Button variant="outline" onClick={onCancel}>
            Cancel
          </Button>
          <Button onClick={handleSave} disabled={saving}>
            {saving ? 'Saving...' : 'Save Schema'}
          </Button>
        </div>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Basic Information</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div>
            <label className="text-sm font-medium">Schema Name</label>
            <Input
              value={schema.name}
              onChange={(e) => setSchema({ ...schema, name: e.target.value })}
              placeholder="e.g., Real Estate Inquiries, Customer Support Cases"
            />
          </div>
          
          <div>
            <label className="text-sm font-medium">Description</label>
            <Textarea
              value={schema.description}
              onChange={(e) => setSchema({ ...schema, description: e.target.value })}
              placeholder="Describe what this schema is used for..."
            />
          </div>

          <div className="flex items-center space-x-2">
            <Switch
              checked={schema.is_default}
              onCheckedChange={(checked) => setSchema({ ...schema, is_default: checked })}
            />
            <label className="text-sm">Set as default schema for new conversations</label>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle>Fields</CardTitle>
            <Button onClick={addField}>
              <Plus className="h-4 w-4 mr-2" />
              Add Field
            </Button>
          </div>
        </CardHeader>
        <CardContent>
          {schema.fields.length === 0 ? (
            <div className="text-center py-8 text-gray-500">
              No fields defined. Click "Add Field" to get started.
            </div>
          ) : (
            <div className="space-y-4">
              {schema.fields.map((field, index) => renderFieldEditor(field, index))}
            </div>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Status Workflow</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="text-sm text-gray-600 mb-4">
            Default statuses are configured. Advanced workflow configuration coming soon.
          </div>
          <div className="flex flex-wrap gap-2">
            {DEFAULT_STATUSES.map((status) => (
              <Badge key={status.id} variant="secondary">
                {status.label}
              </Badge>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  )
}

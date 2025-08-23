'use client'

import { useState, useEffect } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from './ui/card'
import { Button } from './ui/button'
import { Input } from './ui/input'
import { Label } from './ui/label'
import { PlusCircle, Edit, Trash2, Copy, Settings, CheckCircle, AlertCircle, FileText } from 'lucide-react'
import { getContextSchemas, createContextSchema, updateContextSchema, deleteContextSchema } from '@/lib/api'

interface ContextSchema {
  id: string
  name: string
  description: string
  is_active: boolean
  is_default: boolean
  fields: any[]
  status_workflow: any
  created_at: string
  updated_at: string
}

interface ContextSchemasManagerProps {
  workspaceId: string
}

export default function ContextSchemasManager({ workspaceId }: ContextSchemasManagerProps) {
  const [schemas, setSchemas] = useState<ContextSchema[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [showCreateForm, setShowCreateForm] = useState(false)
  const [editingSchema, setEditingSchema] = useState<ContextSchema | null>(null)
  const [formData, setFormData] = useState({
    name: '',
    description: '',
    is_active: true,
    is_default: false
  })

  useEffect(() => {
    loadSchemas()
  }, [workspaceId])

  const loadSchemas = async () => {
    try {
      setIsLoading(true)
      const data = await getContextSchemas(workspaceId)
      setSchemas(Array.isArray(data) ? data : data.results || [])
    } catch (error) {
      console.error('Failed to load schemas:', error)
    } finally {
      setIsLoading(false)
    }
  }

  const handleCreateSchema = async () => {
    try {
      await createContextSchema(workspaceId, formData)
      await loadSchemas()
      setShowCreateForm(false)
      setFormData({ name: '', description: '', is_active: true, is_default: false })
    } catch (error) {
      console.error('Failed to create schema:', error)
    }
  }

  const handleUpdateSchema = async (schemaId: string) => {
    try {
      await updateContextSchema(workspaceId, schemaId, formData)
      await loadSchemas()
      setEditingSchema(null)
      setFormData({ name: '', description: '', is_active: true, is_default: false })
    } catch (error) {
      console.error('Failed to update schema:', error)
    }
  }

  const handleDeleteSchema = async (schemaId: string) => {
    if (!confirm('Are you sure you want to delete this schema?')) return

    try {
      await deleteContextSchema(workspaceId, schemaId)
      await loadSchemas()
    } catch (error) {
      console.error('Failed to delete schema:', error)
    }
  }

  const handleDuplicateSchema = async (schema: ContextSchema) => {
    const duplicateData = {
      ...formData,
      name: `${schema.name} (Copy)`,
      description: schema.description,
      fields: schema.fields,
      status_workflow: schema.status_workflow
    }

    try {
      await createContextSchema(workspaceId, duplicateData)
      await loadSchemas()
    } catch (error) {
      console.error('Failed to duplicate schema:', error)
    }
  }

  const openEditForm = (schema: ContextSchema) => {
    setEditingSchema(schema)
    setFormData({
      name: schema.name,
      description: schema.description,
      is_active: schema.is_active,
      is_default: schema.is_default
    })
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="text-center">
          <div className="w-8 h-8 border-2 border-blue-600 border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
          <p className="text-gray-600">Loading schemas...</p>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <div>
          <h3 className="text-lg font-semibold text-gray-900">Context Schemas</h3>
          <p className="text-sm text-gray-600">Manage dynamic context schemas for your workspace</p>
        </div>
        <Button onClick={() => setShowCreateForm(true)} className="flex items-center space-x-2">
          <PlusCircle className="w-4 h-4" />
          <span>Create Schema</span>
        </Button>
      </div>

      {/* Create/Edit Form */}
      {(showCreateForm || editingSchema) && (
        <Card>
          <CardHeader>
            <CardTitle>{editingSchema ? 'Edit Schema' : 'Create New Schema'}</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <Label htmlFor="name">Schema Name</Label>
                <Input
                  id="name"
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  placeholder="e.g., Customer Support Schema"
                />
              </div>
              <div>
                <Label htmlFor="description">Description</Label>
                <Input
                  id="description"
                  value={formData.description}
                  onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                  placeholder="Brief description of the schema"
                />
              </div>
            </div>
            
            <div className="flex items-center space-x-4">
              <div className="flex items-center space-x-2">
                <input
                  type="checkbox"
                  id="is_active"
                  checked={formData.is_active}
                  onChange={(e) => setFormData({ ...formData, is_active: e.target.checked })}
                  className="rounded border-gray-300"
                />
                <Label htmlFor="is_active">Active</Label>
              </div>
              <div className="flex items-center space-x-2">
                <input
                  type="checkbox"
                  id="is_default"
                  checked={formData.is_default}
                  onChange={(e) => setFormData({ ...formData, is_default: e.target.checked })}
                  className="rounded border-gray-300"
                />
                <Label htmlFor="is_default">Default Schema</Label>
              </div>
            </div>

            <div className="flex space-x-2">
              <Button 
                onClick={() => editingSchema ? handleUpdateSchema(editingSchema.id) : handleCreateSchema()}
                className="flex-1"
              >
                {editingSchema ? 'Update Schema' : 'Create Schema'}
              </Button>
              <Button 
                variant="outline" 
                onClick={() => {
                  setShowCreateForm(false)
                  setEditingSchema(null)
                  setFormData({ name: '', description: '', is_active: true, is_default: false })
                }}
              >
                Cancel
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Schemas List */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {schemas.map((schema) => (
          <Card key={schema.id} className="hover:shadow-md transition-shadow">
            <CardHeader className="pb-3">
              <div className="flex justify-between items-start">
                <div className="flex-1">
                  <CardTitle className="text-lg flex items-center space-x-2">
                    <span>{schema.name}</span>
                    {schema.is_default && (
                      <CheckCircle className="w-4 h-4 text-green-600" />
                    )}
                    {!schema.is_active && (
                      <AlertCircle className="w-4 h-4 text-yellow-600" />
                    )}
                  </CardTitle>
                  <p className="text-sm text-gray-600 mt-1">{schema.description}</p>
                </div>
                <div className="flex space-x-1">
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => openEditForm(schema)}
                    title="Edit Schema"
                  >
                    <Edit className="w-4 h-4" />
                  </Button>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => handleDuplicateSchema(schema)}
                    title="Duplicate Schema"
                  >
                    <Copy className="w-4 h-4" />
                  </Button>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => handleDeleteSchema(schema.id)}
                    title="Delete Schema"
                    className="text-red-600 hover:text-red-700"
                  >
                    <Trash2 className="w-4 h-4" />
                  </Button>
                </div>
              </div>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                <div className="flex justify-between text-sm">
                  <span className="text-gray-600">Fields:</span>
                  <span className="font-medium">{schema.fields?.length || 0}</span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-gray-600">Status Workflow:</span>
                  <span className="font-medium">{schema.status_workflow?.statuses?.length || 0} statuses</span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-gray-600">Created:</span>
                  <span className="font-medium">{new Date(schema.created_at).toLocaleDateString()}</span>
                </div>
              </div>
              
              <div className="mt-4 pt-3 border-t border-gray-200">
                <Button variant="outline" size="sm" className="w-full">
                  <Settings className="w-4 h-4 mr-2" />
                  Configure Fields
                </Button>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      {schemas.length === 0 && (
        <div className="text-center py-12">
          <FileText className="w-12 h-12 text-gray-400 mx-auto mb-4" />
          <p className="text-gray-500">No schemas created yet</p>
          <p className="text-sm text-gray-400">Create your first schema to get started</p>
        </div>
      )}
    </div>
  )
}

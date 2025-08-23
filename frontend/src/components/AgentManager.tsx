'use client'

import { useState, useEffect } from 'react'
import { 
  Plus, 
  Edit, 
  Trash2, 
  Play, 
  Pause, 
  Star, 
  Settings, 
  Bot,
  Globe,
  MessageSquare
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Textarea } from '@/components/ui/textarea'

interface AIAgent {
  id: string
  name: string
  slug: string
  description: string
  channel_type: string
  is_active: boolean
  is_default: boolean
  conversation_count: number
  average_response_time: number
  customer_satisfaction_score: number
  created_at: string
}

interface AgentFormData {
  name: string
  slug: string
  description: string
  channel_type: string
  custom_instructions: string
  is_default: boolean
}

const CHANNEL_TYPES = [
  { value: 'website', label: 'Website Chat', icon: Globe },
  { value: 'whatsapp', label: 'WhatsApp', icon: MessageSquare },
  { value: 'instagram', label: 'Instagram', icon: MessageSquare },
  { value: 'facebook', label: 'Facebook Messenger', icon: MessageSquare },
  { value: 'telegram', label: 'Telegram', icon: MessageSquare },
  { value: 'sms', label: 'SMS', icon: MessageSquare },
  { value: 'email', label: 'Email', icon: MessageSquare },
  { value: 'phone', label: 'Phone Call', icon: MessageSquare }
]

export default function AgentManager({ workspaceId }: { workspaceId: string }) {
  const [agents, setAgents] = useState<AIAgent[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [showForm, setShowForm] = useState(false)
  const [editingAgent, setEditingAgent] = useState<AIAgent | null>(null)
  const [formData, setFormData] = useState<AgentFormData>({
    name: '',
    slug: '',
    description: '',
    channel_type: 'website',
    custom_instructions: '',
    is_default: false
  })

  useEffect(() => {
    loadAgents()
  }, [workspaceId, loadAgents])

  const loadAgents = async () => {
    try {
      setIsLoading(true)
      const response = await fetch(`/api/v1/core/workspaces/${workspaceId}/agents/`, {
        headers: {
          'Authorization': `Token ${localStorage.getItem('authToken')}`
        }
      })
      
      if (response.ok) {
        const data = await response.json()
        setAgents(data.results || data)
      } else {
        console.error('Failed to load agents:', response.statusText)
      }
    } catch (error) {
      console.error('Error loading agents:', error)
    } finally {
      setIsLoading(false)
    }
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    
    try {
      const url = editingAgent 
        ? `/api/v1/core/workspaces/${workspaceId}/agents/${editingAgent.id}/`
        : `/api/v1/core/workspaces/${workspaceId}/agents/`
      
      const method = editingAgent ? 'PUT' : 'POST'
      
      const response = await fetch(url, {
        method,
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Token ${localStorage.getItem('authToken')}`
        },
        body: JSON.stringify({
          ...formData,
          workspace: workspaceId
        })
      })
      
      if (response.ok) {
        await loadAgents()
        resetForm()
        setShowForm(false)
      } else {
        const errorData = await response.json()
        console.error('Failed to save agent:', errorData)
        alert(`Failed to save agent: ${JSON.stringify(errorData)}`)
      }
    } catch (error) {
      console.error('Error saving agent:', error)
      alert('Error saving agent')
    }
  }

  const handleDelete = async (agentId: string) => {
    if (!confirm('Are you sure you want to delete this agent?')) return
    
    try {
      const response = await fetch(`/api/v1/core/workspaces/${workspaceId}/agents/${agentId}/`, {
        method: 'DELETE',
        headers: {
          'Authorization': `Token ${localStorage.getItem('authToken')}`
        }
      })
      
      if (response.ok) {
        await loadAgents()
      } else {
        console.error('Failed to delete agent:', response.statusText)
        alert('Failed to delete agent')
      }
    } catch (error) {
      console.error('Error deleting agent:', error)
      alert('Error deleting agent')
    }
  }

  const handleToggleActive = async (agentId: string) => {
    try {
      const response = await fetch(`/api/v1/core/workspaces/${workspaceId}/agents/${agentId}/toggle-active/`, {
        method: 'POST',
        headers: {
          'Authorization': `Token ${localStorage.getItem('authToken')}`
        }
      })
      
      if (response.ok) {
        await loadAgents()
      } else {
        console.error('Failed to toggle agent status:', response.statusText)
      }
    } catch (error) {
      console.error('Error toggling agent status:', error)
    }
  }

  const handleSetDefault = async (agentId: string) => {
    try {
      const response = await fetch(`/api/v1/core/workspaces/${workspaceId}/agents/${agentId}/set-default/`, {
        method: 'POST',
        headers: {
          'Authorization': `Token ${localStorage.getItem('authToken')}`
        }
      })
      
      if (response.ok) {
        await loadAgents()
      } else {
        console.error('Failed to set default agent:', response.statusText)
      }
    } catch (error) {
      console.error('Error setting default agent:', error)
    }
  }

  const editAgent = (agent: AIAgent) => {
    setEditingAgent(agent)
    setFormData({
      name: agent.name,
      slug: agent.slug,
      description: agent.description,
      channel_type: agent.channel_type,
      custom_instructions: '', // This field might not exist in the current model
      is_default: agent.is_default
    })
    setShowForm(true)
  }

  const resetForm = () => {
    setFormData({
      name: '',
      slug: '',
      description: '',
      channel_type: 'website',
      custom_instructions: '',
      is_default: false
    })
    setEditingAgent(null)
  }

  const generateSlug = (name: string) => {
    return name.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '')
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-8">
        <div className="w-6 h-6 border-2 border-blue-600 border-t-transparent rounded-full animate-spin"></div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex justify-between items-center">
        <div>
          <h2 className="text-2xl font-bold text-gray-900">AI Agents</h2>
          <p className="text-gray-600">Manage your AI agents for different channels and purposes</p>
        </div>
        <Button onClick={() => setShowForm(true)} className="flex items-center space-x-2">
          <Plus className="w-4 h-4" />
          <span>New Agent</span>
        </Button>
      </div>

      {/* Agent Form */}
      {showForm && (
        <Card>
          <CardHeader>
            <CardTitle>{editingAgent ? 'Edit Agent' : 'Create New Agent'}</CardTitle>
            <CardDescription>
              Configure your AI agent's personality, channel, and behavior
            </CardDescription>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleSubmit} className="space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <Label htmlFor="name">Agent Name</Label>
                  <Input
                    id="name"
                    value={formData.name}
                    onChange={(e) => {
                      setFormData({ ...formData, name: e.target.value })
                      if (!editingAgent) {
                        setFormData(prev => ({ ...prev, slug: generateSlug(e.target.value) }))
                      }
                    }}
                    placeholder="e.g., Customer Support Bot"
                    required
                  />
                </div>
                <div>
                  <Label htmlFor="slug">Slug</Label>
                  <Input
                    id="slug"
                    value={formData.slug}
                    onChange={(e) => setFormData({ ...formData, slug: e.target.value })}
                    placeholder="e.g., customer-support-bot"
                    required
                  />
                </div>
              </div>
              
              <div>
                <Label htmlFor="description">Description</Label>
                <Textarea
                  id="description"
                  value={formData.description}
                  onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                  placeholder="Describe what this agent does and how it helps customers"
                  rows={3}
                />
              </div>
              
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <Label htmlFor="channel_type">Channel Type</Label>
                  <Select
                    value={formData.channel_type}
                    onValueChange={(value) => setFormData({ ...formData, channel_type: value })}
                  >
                    <SelectTrigger>
                      <SelectValue placeholder="Select channel type" />
                    </SelectTrigger>
                    <SelectContent>
                      {CHANNEL_TYPES.map((channel) => {
                        const Icon = channel.icon
                        return (
                          <SelectItem key={channel.value} value={channel.value}>
                            <div className="flex items-center space-x-2">
                              <Icon className="w-4 h-4" />
                              <span>{channel.label}</span>
                            </div>
                          </SelectItem>
                        )
                      })}
                    </SelectContent>
                  </Select>
                </div>
                
                <div className="flex items-center space-x-2">
                  <input
                    type="checkbox"
                    id="is_default"
                    checked={formData.is_default}
                    onChange={(e) => setFormData({ ...formData, is_default: e.target.checked })}
                    className="rounded border-gray-300"
                  />
                  <Label htmlFor="is_default">Set as default agent</Label>
                </div>
              </div>
              
              <div>
                <Label htmlFor="custom_instructions">Custom Instructions</Label>
                <Textarea
                  id="custom_instructions"
                  value={formData.custom_instructions}
                  onChange={(e) => setFormData({ ...formData, custom_instructions: e.target.value })}
                  placeholder="Any specific instructions or personality traits for this agent..."
                  rows={4}
                />
              </div>
              
              <div className="flex justify-end space-x-3">
                <Button type="button" variant="outline" onClick={() => {
                  setShowForm(false)
                  resetForm()
                }}>
                  Cancel
                </Button>
                <Button type="submit">
                  {editingAgent ? 'Update Agent' : 'Create Agent'}
                </Button>
              </div>
            </form>
          </CardContent>
        </Card>
      )}

      {/* Agents List */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {agents.map((agent) => (
          <Card key={agent.id} className="relative">
            <CardHeader>
              <div className="flex items-start justify-between">
                <div className="flex items-center space-x-2">
                  <Bot className="w-5 h-5 text-blue-600" />
                  <div>
                    <CardTitle className="text-lg">{agent.name}</CardTitle>
                    <CardDescription className="text-sm">
                      {agent.description || 'No description'}
                    </CardDescription>
                  </div>
                </div>
                <div className="flex items-center space-x-1">
                  {agent.is_default && (
                    <Star className="w-4 h-4 text-yellow-500 fill-current" />
                  )}
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => editAgent(agent)}
                  >
                    <Edit className="w-4 h-4" />
                  </Button>
                </div>
              </div>
            </CardHeader>
            
            <CardContent className="space-y-4">
                             {/* Channel Type */}
               <div className="flex items-center space-x-2 text-sm text-gray-600">
                 {(() => {
                   const channel = CHANNEL_TYPES.find(c => c.value === agent.channel_type)
                   if (channel) {
                     const Icon = channel.icon
                     return <Icon className="w-4 h-4" />
                   }
                   return null
                 })()}
                 <span className="capitalize">{agent.channel_type}</span>
               </div>
              
              {/* Status */}
              <div className="flex items-center space-x-2">
                <div className={`w-2 h-2 rounded-full ${agent.is_active ? 'bg-green-500' : 'bg-red-500'}`} />
                <span className="text-sm text-gray-600">
                  {agent.is_active ? 'Active' : 'Inactive'}
                </span>
              </div>
              
              {/* Metrics */}
              <div className="grid grid-cols-3 gap-4 text-sm">
                <div className="text-center">
                  <div className="font-semibold text-gray-900">{agent.conversation_count}</div>
                  <div className="text-gray-500">Conversations</div>
                </div>
                <div className="text-center">
                  <div className="font-semibold text-gray-900">{agent.average_response_time.toFixed(1)}s</div>
                  <div className="text-gray-500">Avg Response</div>
                </div>
                <div className="text-center">
                  <div className="font-semibold text-gray-900">{agent.customer_satisfaction_score.toFixed(1)}</div>
                  <div className="text-gray-500">Satisfaction</div>
                </div>
              </div>
              
              {/* Actions */}
              <div className="flex space-x-2 pt-2 border-t">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => handleToggleActive(agent.id)}
                  className="flex-1"
                >
                  {agent.is_active ? <Pause className="w-4 h-4" /> : <Play className="w-4 h-4" />}
                  <span className="ml-1">{agent.is_active ? 'Pause' : 'Activate'}</span>
                </Button>
                
                {!agent.is_default && (
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => handleSetDefault(agent.id)}
                    className="flex-1"
                  >
                    <Star className="w-4 h-4" />
                    <span className="ml-1">Set Default</span>
                  </Button>
                )}
                
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => editAgent(agent)}
                >
                  <Settings className="w-4 h-4" />
                </Button>
                
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => handleDelete(agent.id)}
                  className="text-red-600 hover:text-red-700"
                >
                  <Trash2 className="w-4 h-4" />
                </Button>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Empty State */}
      {agents.length === 0 && !showForm && (
        <Card className="text-center py-12">
          <CardContent>
            <Bot className="w-12 h-12 text-gray-400 mx-auto mb-4" />
            <h3 className="text-lg font-medium text-gray-900 mb-2">No AI Agents Yet</h3>
            <p className="text-gray-600 mb-4">
              Create your first AI agent to start automating customer interactions
            </p>
            <Button onClick={() => setShowForm(true)}>
              <Plus className="w-4 h-4 mr-2" />
              Create Your First Agent
            </Button>
          </CardContent>
        </Card>
      )}
    </div>
  )
}

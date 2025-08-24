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

import { Textarea } from '@/components/ui/textarea'

// API Configuration
const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE || 'http://localhost:8000'

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
  custom_instructions: string
  business_context: Record<string, any>
  personality_config: Record<string, any>
  channel_specific_config: Record<string, any>
  generated_prompt: string
  prompt_version: string
}

interface AgentFormData {
  name: string
  slug: string
  description: string
  channel_type: string
  custom_instructions: string
  business_context: {
    services: string[]
    target_audience: string
    key_values: string[]
    expertise_areas: string[]
    operating_hours: string
    special_instructions: string
  }
  personality_config: {
    tone: string
    formality: string
    empathy_level: string
    proactiveness: string
    expertise_level: string
    custom_traits: string
  }
  channel_specific_config: {
    response_style: string
    max_response_length: number
    use_emojis: boolean
    greeting_message: string
    escalation_triggers: string[]
  }
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
    business_context: {
      services: [],
      target_audience: '',
      key_values: [],
      expertise_areas: [],
      operating_hours: '',
      special_instructions: ''
    },
    personality_config: {
      tone: 'professional',
      formality: 'balanced',
      empathy_level: 'moderate',
      proactiveness: 'standard',
      expertise_level: 'knowledgeable',
      custom_traits: ''
    },
    channel_specific_config: {
      response_style: 'conversational',
      max_response_length: 200,
      use_emojis: false,
      greeting_message: '',
      escalation_triggers: []
    }
  })

  const loadAgents = async () => {
    try {
      setIsLoading(true)
      const response = await fetch(`${API_BASE_URL}/api/v1/core/workspace/${workspaceId}/agents/`, {
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

  useEffect(() => {
    if (workspaceId) {
      loadAgents()
    }
  }, [workspaceId])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    
    try {
      const url = editingAgent 
        ? `${API_BASE_URL}/api/v1/core/workspace/${workspaceId}/agents/${editingAgent.id}/`
        : `${API_BASE_URL}/api/v1/core/workspace/${workspaceId}/agents/`
      
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
      const response = await fetch(`${API_BASE_URL}/api/v1/core/workspace/${workspaceId}/agents/${agentId}/`, {
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
      const response = await fetch(`${API_BASE_URL}/api/v1/core/workspace/${workspaceId}/agents/${agentId}/toggle-active/`, {
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
      const response = await fetch(`${API_BASE_URL}/api/v1/core/workspace/${workspaceId}/agents/${agentId}/set-default/`, {
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
      custom_instructions: agent.custom_instructions || '',
      business_context: {
        services: agent.business_context?.services || [],
        target_audience: agent.business_context?.target_audience || '',
        key_values: agent.business_context?.key_values || [],
        expertise_areas: agent.business_context?.expertise_areas || [],
        operating_hours: agent.business_context?.operating_hours || '',
        special_instructions: agent.business_context?.special_instructions || ''
      },
      personality_config: {
        tone: agent.personality_config?.tone || 'professional',
        formality: agent.personality_config?.formality || 'balanced',
        empathy_level: agent.personality_config?.empathy_level || 'moderate',
        proactiveness: agent.personality_config?.proactiveness || 'standard',
        expertise_level: agent.personality_config?.expertise_level || 'knowledgeable',
        custom_traits: agent.personality_config?.custom_traits || ''
      },
      channel_specific_config: {
        response_style: agent.channel_specific_config?.response_style || 'conversational',
        max_response_length: agent.channel_specific_config?.max_response_length || 200,
        use_emojis: agent.channel_specific_config?.use_emojis || false,
        greeting_message: agent.channel_specific_config?.greeting_message || '',
        escalation_triggers: agent.channel_specific_config?.escalation_triggers || []
      }
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
      business_context: {
        services: [],
        target_audience: '',
        key_values: [],
        expertise_areas: [],
        operating_hours: '',
        special_instructions: ''
      },
      personality_config: {
        tone: 'professional',
        formality: 'balanced',
        empathy_level: 'moderate',
        proactiveness: 'standard',
        expertise_level: 'knowledgeable',
        custom_traits: ''
      },
      channel_specific_config: {
        response_style: 'conversational',
        max_response_length: 200,
        use_emojis: false,
        greeting_message: '',
        escalation_triggers: []
      }
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
      <div className="flex justify-between items-start">
        <div>
          <h2 className="text-2xl font-bold text-gray-900">AI Agents</h2>
          <p className="text-gray-600">Manage your AI agents for different channels and purposes</p>
          {(() => {
            const activeAgents = agents.filter(agent => agent.is_active)
            return (
              <div className="mt-2">
                {activeAgents.length === 0 && (
                  <div className="flex items-center space-x-2 text-amber-700 bg-amber-50 px-3 py-2 rounded-lg">
                    <Bot className="w-4 h-4" />
                    <span className="text-sm">No active agents - Portal will show "AI assistant unavailable"</span>
                  </div>
                )}
                {activeAgents.length === 1 && (
                  <div className="flex items-center space-x-2 text-green-700 bg-green-50 px-3 py-2 rounded-lg">
                    <Bot className="w-4 h-4" />
                    <span className="text-sm">1 active agent: <strong>{activeAgents[0].name}</strong></span>
                  </div>
                )}
                {activeAgents.length > 1 && (
                  <div className="flex items-center space-x-2 text-blue-700 bg-blue-50 px-3 py-2 rounded-lg">
                    <Bot className="w-4 h-4" />
                    <span className="text-sm">{activeAgents.length} active agents</span>
                  </div>
                )}
              </div>
            )
          })()}
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
                  <select
                    id="channel_type"
                    value={formData.channel_type}
                    onChange={(e) => setFormData({ ...formData, channel_type: e.target.value })}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  >
                    {CHANNEL_TYPES.map((channel) => (
                      <option key={channel.value} value={channel.value}>
                        {channel.label}
                      </option>
                    ))}
                  </select>
                </div>
                
                <div className="text-sm text-gray-600">
                  <p>💡 Tip: Use "Activate" to make this agent handle customer conversations</p>
                </div>
              </div>
              
              {/* Personality Configuration */}
              <div className="border rounded-lg p-4 space-y-4">
                <h3 className="text-lg font-semibold text-gray-900">Personality & Communication Style</h3>
                
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                  <div>
                    <Label htmlFor="tone">Tone</Label>
                    <select
                      id="tone"
                      value={formData.personality_config.tone}
                      onChange={(e) => setFormData({
                        ...formData,
                        personality_config: { ...formData.personality_config, tone: e.target.value }
                      })}
                      className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500"
                    >
                      <option value="professional">Professional</option>
                      <option value="friendly">Friendly</option>
                      <option value="casual">Casual</option>
                      <option value="formal">Formal</option>
                      <option value="empathetic">Empathetic</option>
                    </select>
                  </div>
                  
                  <div>
                    <Label htmlFor="formality">Formality Level</Label>
                    <select
                      id="formality"
                      value={formData.personality_config.formality}
                      onChange={(e) => setFormData({
                        ...formData,
                        personality_config: { ...formData.personality_config, formality: e.target.value }
                      })}
                      className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500"
                    >
                      <option value="formal">Formal</option>
                      <option value="balanced">Balanced</option>
                      <option value="casual">Casual</option>
                    </select>
                  </div>
                  
                  <div>
                    <Label htmlFor="empathy_level">Empathy Level</Label>
                    <select
                      id="empathy_level"
                      value={formData.personality_config.empathy_level}
                      onChange={(e) => setFormData({
                        ...formData,
                        personality_config: { ...formData.personality_config, empathy_level: e.target.value }
                      })}
                      className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500"
                    >
                      <option value="high">High</option>
                      <option value="moderate">Moderate</option>
                      <option value="low">Low</option>
                    </select>
                  </div>
                  
                  <div>
                    <Label htmlFor="proactiveness">Proactiveness</Label>
                    <select
                      id="proactiveness"
                      value={formData.personality_config.proactiveness}
                      onChange={(e) => setFormData({
                        ...formData,
                        personality_config: { ...formData.personality_config, proactiveness: e.target.value }
                      })}
                      className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500"
                    >
                      <option value="high">High</option>
                      <option value="standard">Standard</option>
                      <option value="low">Low</option>
                    </select>
                  </div>
                  
                  <div>
                    <Label htmlFor="expertise_level">Expertise Level</Label>
                    <select
                      id="expertise_level"
                      value={formData.personality_config.expertise_level}
                      onChange={(e) => setFormData({
                        ...formData,
                        personality_config: { ...formData.personality_config, expertise_level: e.target.value }
                      })}
                      className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500"
                    >
                      <option value="expert">Expert</option>
                      <option value="knowledgeable">Knowledgeable</option>
                      <option value="basic">Basic</option>
                    </select>
                  </div>
                </div>
                
                <div>
                  <Label htmlFor="custom_traits">Custom Personality Traits</Label>
                  <Textarea
                    id="custom_traits"
                    value={formData.personality_config.custom_traits}
                    onChange={(e) => setFormData({
                      ...formData,
                      personality_config: { ...formData.personality_config, custom_traits: e.target.value }
                    })}
                    placeholder="e.g., Always includes helpful tips, uses humor appropriately, detail-oriented..."
                    rows={3}
                  />
                </div>
              </div>

              {/* Business Context Configuration */}
              <div className="border rounded-lg p-4 space-y-4">
                <h3 className="text-lg font-semibold text-gray-900">Business Context & Expertise</h3>
                
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <Label htmlFor="target_audience">Target Audience</Label>
                    <Input
                      id="target_audience"
                      value={formData.business_context.target_audience}
                      onChange={(e) => setFormData({
                        ...formData,
                        business_context: { ...formData.business_context, target_audience: e.target.value }
                      })}
                      placeholder="e.g., Banking customers and potential clients"
                    />
                  </div>
                  
                  <div>
                    <Label htmlFor="operating_hours">Operating Hours</Label>
                    <Input
                      id="operating_hours"
                      value={formData.business_context.operating_hours}
                      onChange={(e) => setFormData({
                        ...formData,
                        business_context: { ...formData.business_context, operating_hours: e.target.value }
                      })}
                      placeholder="e.g., Monday-Friday 9AM-5PM"
                    />
                  </div>
                </div>
                
                <div>
                  <Label htmlFor="services">Services Offered (comma-separated)</Label>
                  <Input
                    id="services"
                    value={formData.business_context.services.join(', ')}
                    onChange={(e) => setFormData({
                      ...formData,
                      business_context: {
                        ...formData.business_context,
                        services: e.target.value.split(',').map(s => s.trim()).filter(s => s)
                      }
                    })}
                    placeholder="e.g., Banking Services, Loans, Financial Consultations"
                  />
                </div>
                
                <div>
                  <Label htmlFor="key_values">Company Values (comma-separated)</Label>
                  <Input
                    id="key_values"
                    value={formData.business_context.key_values.join(', ')}
                    onChange={(e) => setFormData({
                      ...formData,
                      business_context: {
                        ...formData.business_context,
                        key_values: e.target.value.split(',').map(s => s.trim()).filter(s => s)
                      }
                    })}
                    placeholder="e.g., Trust, Security, Customer Service"
                  />
                </div>
                
                <div>
                  <Label htmlFor="expertise_areas">Areas of Expertise (comma-separated)</Label>
                  <Input
                    id="expertise_areas"
                    value={formData.business_context.expertise_areas.join(', ')}
                    onChange={(e) => setFormData({
                      ...formData,
                      business_context: {
                        ...formData.business_context,
                        expertise_areas: e.target.value.split(',').map(s => s.trim()).filter(s => s)
                      }
                    })}
                    placeholder="e.g., appointment scheduling, customer service, banking"
                  />
                </div>
                
                <div>
                  <Label htmlFor="special_instructions">Special Business Instructions</Label>
                  <Textarea
                    id="special_instructions"
                    value={formData.business_context.special_instructions}
                    onChange={(e) => setFormData({
                      ...formData,
                      business_context: { ...formData.business_context, special_instructions: e.target.value }
                    })}
                    placeholder="Any specific business rules or special handling instructions..."
                    rows={3}
                  />
                </div>
              </div>

              {/* Channel-Specific Configuration */}
              <div className="border rounded-lg p-4 space-y-4">
                <h3 className="text-lg font-semibold text-gray-900">Channel-Specific Behavior</h3>
                
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                  <div>
                    <Label htmlFor="response_style">Response Style</Label>
                    <select
                      id="response_style"
                      value={formData.channel_specific_config.response_style}
                      onChange={(e) => setFormData({
                        ...formData,
                        channel_specific_config: { ...formData.channel_specific_config, response_style: e.target.value }
                      })}
                      className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500"
                    >
                      <option value="conversational">Conversational</option>
                      <option value="formal">Formal</option>
                      <option value="brief">Brief</option>
                      <option value="detailed">Detailed</option>
                    </select>
                  </div>
                  
                  <div>
                    <Label htmlFor="max_response_length">Max Response Length (words)</Label>
                    <Input
                      id="max_response_length"
                      type="number"
                      value={formData.channel_specific_config.max_response_length}
                      onChange={(e) => setFormData({
                        ...formData,
                        channel_specific_config: { ...formData.channel_specific_config, max_response_length: parseInt(e.target.value) || 200 }
                      })}
                      min="50"
                      max="500"
                    />
                  </div>
                  
                  <div className="flex items-center space-x-2">
                    <input
                      type="checkbox"
                      id="use_emojis"
                      checked={formData.channel_specific_config.use_emojis}
                      onChange={(e) => setFormData({
                        ...formData,
                        channel_specific_config: { ...formData.channel_specific_config, use_emojis: e.target.checked }
                      })}
                      className="rounded border-gray-300 focus:ring-2 focus:ring-blue-500"
                    />
                    <Label htmlFor="use_emojis">Use Emojis</Label>
                  </div>
                </div>
                
                <div>
                  <Label htmlFor="greeting_message">Custom Greeting Message</Label>
                  <Input
                    id="greeting_message"
                    value={formData.channel_specific_config.greeting_message}
                    onChange={(e) => setFormData({
                      ...formData,
                      channel_specific_config: { ...formData.channel_specific_config, greeting_message: e.target.value }
                    })}
                    placeholder="e.g., Hello! I'm [Agent Name] from [Company]. How can I help you today?"
                  />
                </div>
                
                <div>
                  <Label htmlFor="escalation_triggers">Escalation Triggers (comma-separated)</Label>
                  <Input
                    id="escalation_triggers"
                    value={formData.channel_specific_config.escalation_triggers.join(', ')}
                    onChange={(e) => setFormData({
                      ...formData,
                      channel_specific_config: {
                        ...formData.channel_specific_config,
                        escalation_triggers: e.target.value.split(',').map(s => s.trim()).filter(s => s)
                      }
                    })}
                    placeholder="e.g., fraud, security breach, legal issue, complex problem"
                  />
                </div>
              </div>
              
              {/* Custom Instructions */}
              <div>
                <Label htmlFor="custom_instructions">Additional Custom Instructions</Label>
                <Textarea
                  id="custom_instructions"
                  value={formData.custom_instructions}
                  onChange={(e) => setFormData({ ...formData, custom_instructions: e.target.value })}
                  placeholder="Any additional specific instructions or special behaviors for this agent..."
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
              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-2">
                  <div className={`w-3 h-3 rounded-full ${agent.is_active ? 'bg-green-500' : 'bg-red-500'}`} />
                  <span className={`text-sm font-medium ${agent.is_active ? 'text-green-700' : 'text-red-700'}`}>
                    {agent.is_active ? 'Active' : 'Inactive'}
                  </span>
                </div>
                {agent.is_active && (
                  <span className="text-xs bg-green-100 text-green-800 px-2 py-1 rounded-full">
                    Handling Portal
                  </span>
                )}
              </div>
              
              {/* Enhanced Configuration Info */}
              {(agent.personality_config || agent.business_context) && (
                <div className="space-y-2 text-xs bg-gray-50 rounded-lg p-3">
                  {agent.personality_config && (
                    <div className="flex items-center space-x-4">
                      <span className="font-medium text-gray-700">Personality:</span>
                      <div className="flex space-x-2">
                        {agent.personality_config.tone && (
                          <span className="bg-blue-100 text-blue-800 px-2 py-1 rounded-full capitalize">
                            {agent.personality_config.tone}
                          </span>
                        )}
                        {agent.personality_config.expertise_level && (
                          <span className="bg-purple-100 text-purple-800 px-2 py-1 rounded-full capitalize">
                            {agent.personality_config.expertise_level}
                          </span>
                        )}
                      </div>
                    </div>
                  )}
                  {agent.business_context?.services && agent.business_context.services.length > 0 && (
                    <div className="flex items-start space-x-2">
                      <span className="font-medium text-gray-700">Services:</span>
                      <span className="text-gray-600 text-xs">
                        {agent.business_context.services.slice(0, 2).join(', ')}
                        {agent.business_context.services.length > 2 && ` +${agent.business_context.services.length - 2} more`}
                      </span>
                    </div>
                  )}
                  {agent.channel_specific_config?.use_emojis && (
                    <div className="flex items-center space-x-2">
                      <span className="text-green-600">😊</span>
                      <span className="text-gray-600">Emoji-friendly</span>
                    </div>
                  )}
                </div>
              )}
              
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
                  variant={agent.is_active ? "destructive" : "default"}
                  size="sm"
                  onClick={() => handleToggleActive(agent.id)}
                  className="flex-1"
                >
                  {agent.is_active ? <Pause className="w-4 h-4" /> : <Play className="w-4 h-4" />}
                  <span className="ml-1">{agent.is_active ? 'Deactivate' : 'Activate'}</span>
                </Button>
                
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

'use client'

import { useState, useEffect } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from './ui/card'
import { Button } from './ui/button'
import { Input } from './ui/input'
import { Label } from './ui/label'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from './ui/select'
import { Textarea } from './ui/textarea'
import { PlusCircle, Edit, Trash2, Play, Pause, Settings, Bot, CheckCircle, AlertCircle } from 'lucide-react'
import { getBusinessRules, createBusinessRule, updateBusinessRule, deleteBusinessRule, toggleBusinessRule, testBusinessRule } from '@/lib/api'

interface BusinessRule {
  id: string
  name: string
  description: string
  trigger_type: string
  is_active: boolean
  is_default: boolean
  priority: number
  execution_count: number
  success_rate: number
  average_execution_time: number
  created_at: string
  updated_at: string
  actions: any[]
  workflow_steps?: any[]
}

interface BusinessRulesManagerProps {
  workspaceId: string
}

export default function BusinessRulesManager({ workspaceId }: BusinessRulesManagerProps) {
  const [rules, setRules] = useState<BusinessRule[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [showCreateForm, setShowCreateForm] = useState(false)
  const [editingRule, setEditingRule] = useState<BusinessRule | null>(null)
  const [formData, setFormData] = useState({
    name: '',
    description: '',
    trigger_type: 'new_message',
    is_active: true,
    is_default: false,
    priority: 1
  })

  useEffect(() => {
    loadRules()
  }, [workspaceId])

  const loadRules = async () => {
    try {
      setIsLoading(true)
      const data = await getBusinessRules(workspaceId)
      setRules(Array.isArray(data) ? data : data.results || [])
    } catch (error) {
      console.error('Failed to load rules:', error)
    } finally {
      setIsLoading(false)
    }
  }

  const handleCreateRule = async () => {
    try {
      await createBusinessRule(workspaceId, formData)
      await loadRules()
      setShowCreateForm(false)
      setFormData({ name: '', description: '', trigger_type: 'new_message', is_active: true, is_default: false, priority: 1 })
    } catch (error) {
      console.error('Failed to create rule:', error)
    }
  }

  const handleUpdateRule = async (ruleId: string) => {
    try {
      await updateBusinessRule(workspaceId, ruleId, formData)
      await loadRules()
      setEditingRule(null)
      setFormData({ name: '', description: '', trigger_type: 'new_message', is_active: true, is_default: false, priority: 1 })
    } catch (error) {
      console.error('Failed to update rule:', error)
    }
  }

  const handleDeleteRule = async (ruleId: string) => {
    if (!confirm('Are you sure you want to delete this rule?')) return

    try {
      await deleteBusinessRule(workspaceId, ruleId)
      await loadRules()
    } catch (error) {
      console.error('Failed to delete rule:', error)
    }
  }

  const handleToggleRule = async (ruleId: string, isActive: boolean) => {
    try {
      await toggleBusinessRule(workspaceId, ruleId, !isActive)
      await loadRules()
    } catch (error) {
      console.error('Failed to toggle rule:', error)
    }
  }

  const handleTestRule = async (ruleId: string) => {
    try {
      await testBusinessRule(workspaceId, ruleId)
      alert('Rule test executed successfully!')
    } catch (error) {
      console.error('Failed to test rule:', error)
      alert('Rule test failed. Check console for details.')
    }
  }

  const openEditForm = (rule: BusinessRule) => {
    setEditingRule(rule)
    setFormData({
      name: rule.name,
      description: rule.description,
      trigger_type: rule.trigger_type,
      is_active: rule.is_active,
      is_default: rule.is_default,
      priority: rule.priority
    })
  }

  const getTriggerTypeLabel = (triggerType: string) => {
    const labels: { [key: string]: string } = {
      'new_message': 'New Message',
      'context_change': 'Context Change',
      'status_change': 'Status Change',
      'priority_change': 'Priority Change',
      'completion_rate': 'Completion Rate',
      'field_dependency': 'Field Dependency',
      'schedule': 'Schedule',
      'external_webhook': 'External Webhook',
      'conversation_age': 'Conversation Age',
      'response_time': 'Response Time',
      'customer_satisfaction': 'Customer Satisfaction',
      'business_hours': 'Business Hours',
      'workload_balance': 'Workload Balance'
    }
    return labels[triggerType] || triggerType
  }

  const getPriorityColor = (priority: number) => {
    if (priority >= 8) return 'text-red-600 bg-red-100'
    if (priority >= 6) return 'text-orange-600 bg-orange-100'
    if (priority >= 4) return 'text-yellow-600 bg-yellow-100'
    return 'text-green-600 bg-green-100'
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="text-center">
          <div className="w-8 h-8 border-2 border-blue-600 border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
          <p className="text-gray-600">Loading business rules...</p>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <div>
          <h3 className="text-lg font-semibold text-gray-900">Business Rules</h3>
          <p className="text-sm text-gray-600">Manage automated business rules and workflows</p>
        </div>
        <Button onClick={() => setShowCreateForm(true)} className="flex items-center space-x-2">
          <PlusCircle className="w-4 h-4" />
          <span>Create Rule</span>
        </Button>
      </div>

      {/* Create/Edit Form */}
      {(showCreateForm || editingRule) && (
        <Card>
          <CardHeader>
            <CardTitle>{editingRule ? 'Edit Business Rule' : 'Create New Business Rule'}</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <Label htmlFor="name">Rule Name</Label>
                <Input
                  id="name"
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  placeholder="e.g., High Priority Escalation"
                />
              </div>
              <div>
                <Label htmlFor="trigger_type">Trigger Type</Label>
                <Select value={formData.trigger_type} onValueChange={(value) => setFormData({ ...formData, trigger_type: value })}>
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="new_message">New Message</SelectItem>
                    <SelectItem value="context_change">Context Change</SelectItem>
                    <SelectItem value="status_change">Status Change</SelectItem>
                    <SelectItem value="priority_change">Priority Change</SelectItem>
                    <SelectItem value="completion_rate">Completion Rate</SelectItem>
                    <SelectItem value="field_dependency">Field Dependency</SelectItem>
                    <SelectItem value="schedule">Schedule</SelectItem>
                    <SelectItem value="external_webhook">External Webhook</SelectItem>
                    <SelectItem value="conversation_age">Conversation Age</SelectItem>
                    <SelectItem value="response_time">Response Time</SelectItem>
                    <SelectItem value="customer_satisfaction">Customer Satisfaction</SelectItem>
                    <SelectItem value="business_hours">Business Hours</SelectItem>
                    <SelectItem value="workload_balance">Workload Balance</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>
            
            <div>
              <Label htmlFor="description">Description</Label>
              <Textarea
                id="description"
                value={formData.description}
                onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                placeholder="Describe what this rule does and when it triggers"
                rows={3}
              />
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div>
                <Label htmlFor="priority">Priority (1-10)</Label>
                <Input
                  id="priority"
                  type="number"
                  min="1"
                  max="10"
                  value={formData.priority}
                  onChange={(e) => setFormData({ ...formData, priority: parseInt(e.target.value) })}
                />
              </div>
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
                <Label htmlFor="is_default">Default Rule</Label>
              </div>
            </div>

            <div className="flex space-x-2">
              <Button 
                onClick={() => editingRule ? handleUpdateRule(editingRule.id) : handleCreateRule()}
                className="flex-1"
              >
                {editingRule ? 'Update Rule' : 'Create Rule'}
              </Button>
              <Button 
                variant="outline" 
                onClick={() => {
                  setShowCreateForm(false)
                  setEditingRule(null)
                  setFormData({ name: '', description: '', trigger_type: 'new_message', is_active: true, is_default: false, priority: 1 })
                }}
              >
                Cancel
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Rules List */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {rules.map((rule) => (
          <Card key={rule.id} className="hover:shadow-md transition-shadow">
            <CardHeader className="pb-3">
              <div className="flex justify-between items-start">
                <div className="flex-1">
                  <CardTitle className="text-lg flex items-center space-x-2">
                    <span>{rule.name}</span>
                    {rule.is_default && (
                      <CheckCircle className="w-4 h-4 text-green-600" />
                    )}
                    {!rule.is_active && (
                      <AlertCircle className="w-4 h-4 text-yellow-600" />
                    )}
                  </CardTitle>
                  <p className="text-sm text-gray-600 mt-1">{rule.description}</p>
                </div>
                <div className="flex space-x-1">
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => handleTestRule(rule.id)}
                    title="Test Rule"
                  >
                    <Play className="w-4 h-4" />
                  </Button>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => openEditForm(rule)}
                    title="Edit Rule"
                  >
                    <Edit className="w-4 h-4" />
                  </Button>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => handleToggleRule(rule.id, rule.is_active)}
                    title={rule.is_active ? 'Deactivate' : 'Activate'}
                  >
                    {rule.is_active ? <Pause className="w-4 h-4" /> : <Play className="w-4 h-4" />}
                  </Button>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => handleDeleteRule(rule.id)}
                    title="Delete Rule"
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
                  <span className="text-gray-600">Trigger:</span>
                  <span className="font-medium">{getTriggerTypeLabel(rule.trigger_type)}</span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-gray-600">Priority:</span>
                  <span className={`px-2 py-1 rounded-full text-xs font-medium ${getPriorityColor(rule.priority)}`}>
                    {rule.priority}/10
                  </span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-gray-600">Actions:</span>
                  <span className="font-medium">{rule.actions?.length || 0}</span>
                </div>
                {rule.workflow_steps && rule.workflow_steps.length > 0 && (
                  <div className="flex justify-between text-sm">
                    <span className="text-gray-600">Workflow Steps:</span>
                    <span className="font-medium">{rule.workflow_steps.length}</span>
                  </div>
                )}
                <div className="flex justify-between text-sm">
                  <span className="text-gray-600">Executions:</span>
                  <span className="font-medium">{rule.execution_count || 0}</span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-gray-600">Success Rate:</span>
                  <span className="font-medium">{rule.success_rate ? `${rule.success_rate}%` : 'N/A'}</span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-gray-600">Avg Time:</span>
                  <span className="font-medium">{rule.average_execution_time ? `${rule.average_execution_time}ms` : 'N/A'}</span>
                </div>
              </div>
              
              <div className="mt-4 pt-3 border-t border-gray-200">
                <Button variant="outline" size="sm" className="w-full">
                  <Settings className="w-4 h-4 mr-2" />
                  Configure Actions
                </Button>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      {rules.length === 0 && (
        <div className="text-center py-12">
          <Bot className="w-12 h-12 text-gray-400 mx-auto mb-4" />
          <p className="text-gray-500">No business rules created yet</p>
          <p className="text-sm text-gray-400">Create your first rule to automate your business processes</p>
        </div>
      )}
    </div>
  )
}

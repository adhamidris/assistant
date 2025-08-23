'use client';

import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from './ui/card';
import { Button } from './ui/button';
import { Input } from './ui/input';
import { Label } from './ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from './ui/select';
import { Textarea } from './ui/textarea';
import { Badge } from './ui/badge';

interface ContextField {
  id: string;
  name: string;
  type: string;
  required: boolean;
  choices?: string[];
  value?: any;
  description?: string;
}

interface ConversationContext {
  id: string;
  conversation_id: string;
  context_data: Record<string, any>;
  status: string;
  priority: string;
  tags: string[];
  last_updated: string;
  schema: {
    fields: ContextField[];
    status_workflow: {
      statuses: Array<{ id: string; label: string; color: string }>;
      transitions: Record<string, string[]>;
    };
  };
}

interface ContextSidebarProps {
  conversationId: string;
  onContextUpdate: (context: Partial<ConversationContext>) => void;
}

export default function ContextSidebar({ conversationId, onContextUpdate }: ContextSidebarProps) {
  const [context, setContext] = useState<ConversationContext | null>(null);
  const [loading, setLoading] = useState(true);
  const [editing, setEditing] = useState(false);
  const [newTag, setNewTag] = useState('');

  useEffect(() => {
    // Fetch conversation context
    fetchContext();
  }, [conversationId]);

  const fetchContext = async () => {
    try {
      setLoading(true);
      // TODO: Replace with actual API call
      const response = await fetch(`/api/v1/context-tracking/conversation-contexts/?conversation=${conversationId}`);
      if (response.ok) {
        const data = await response.json();
        if (data.results && data.results.length > 0) {
          setContext(data.results[0]);
        }
      }
    } catch (error) {
      console.error('Failed to fetch context:', error);
    } finally {
      setLoading(false);
    }
  };

  const updateFieldValue = (fieldId: string, value: any) => {
    if (!context) return;
    
    setContext(prev => ({
      ...prev!,
      context_data: {
        ...prev!.context_data,
        [fieldId]: value
      }
    }));
  };

  const updateStatus = (newStatus: string) => {
    if (!context) return;
    
    // Check if transition is allowed
    const currentStatus = context.status;
    const allowedTransitions = context.schema.status_workflow.transitions[currentStatus] || [];
    
    if (!allowedTransitions.includes(newStatus) && newStatus !== currentStatus) {
      alert(`Cannot transition from ${currentStatus} to ${newStatus}`);
      return;
    }
    
    setContext(prev => ({
      ...prev!,
      status: newStatus
    }));
  };

  const updatePriority = (newPriority: string) => {
    if (!context) return;
    
    setContext(prev => ({
      ...prev!,
      priority: newPriority
    }));
  };

  const addTag = () => {
    if (!newTag.trim() || !context) return;
    
    if (!context.tags.includes(newTag.trim())) {
      setContext(prev => ({
        ...prev!,
        tags: [...prev!.tags, newTag.trim()]
      }));
    }
    setNewTag('');
  };

  const removeTag = (tagToRemove: string) => {
    if (!context) return;
    
    setContext(prev => ({
      ...prev!,
      tags: prev!.tags.filter(tag => tag !== tagToRemove)
    }));
  };

  const handleSave = async () => {
    if (!context) return;
    
    try {
      // TODO: Replace with actual API call
      const response = await fetch(`/api/v1/context-tracking/conversation-contexts/${context.id}/`, {
        method: 'PATCH',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          context_data: context.context_data,
          status: context.status,
          priority: context.priority,
          tags: context.tags
        })
      });
      
      if (response.ok) {
        setEditing(false);
        onContextUpdate(context);
      }
    } catch (error) {
      console.error('Failed to save context:', error);
      alert('Failed to save context changes');
    }
  };

  const renderFieldInput = (field: ContextField) => {
    const value = context?.context_data[field.id];
    
    switch (field.type) {
      case 'text':
      case 'email':
      case 'phone':
      case 'url':
        return (
          <Input
            value={value || ''}
            onChange={(e) => updateFieldValue(field.id, e.target.value)}
            placeholder={field.description || `Enter ${field.name.toLowerCase()}`}
            disabled={!editing}
          />
        );
      
      case 'textarea':
        return (
          <Textarea
            value={value || ''}
            onChange={(e) => updateFieldValue(field.id, e.target.value)}
            placeholder={field.description || `Enter ${field.name.toLowerCase()}`}
            disabled={!editing}
            rows={3}
          />
        );
      
      case 'choice':
        return (
          <Select
            value={value || ''}
            onChange={(e) => updateFieldValue(field.id, e.target.value)}
            disabled={!editing}
          >
            <option value="">{`Select ${field.name.toLowerCase()}`}</option>
            {field.choices?.map(choice => (
              <option key={choice} value={choice}>
                {choice}
              </option>
            ))}
          </Select>
        );
      
      case 'multi_choice':
        const selectedValues = Array.isArray(value) ? value : [];
        return (
          <div className="space-y-2">
            {field.choices?.map(choice => (
              <label key={choice} className="flex items-center space-x-2">
                <input
                  type="checkbox"
                  checked={selectedValues.includes(choice)}
                  onChange={(e) => {
                    if (e.target.checked) {
                      updateFieldValue(field.id, [...selectedValues, choice]);
                    } else {
                      updateFieldValue(field.id, selectedValues.filter(v => v !== choice));
                    }
                  }}
                  disabled={!editing}
                />
                <span className="text-sm">{choice}</span>
              </label>
            ))}
          </div>
        );
      
      case 'date':
        return (
          <Input
            type="date"
            value={value || ''}
            onChange={(e) => updateFieldValue(field.id, e.target.value)}
            disabled={!editing}
          />
        );
      
      case 'datetime':
        return (
          <Input
            type="datetime-local"
            value={value || ''}
            onChange={(e) => updateFieldValue(field.id, e.target.value)}
            disabled={!editing}
          />
        );
      
      case 'number':
      case 'decimal':
        return (
          <Input
            type="number"
            value={value || ''}
            onChange={(e) => updateFieldValue(field.id, parseFloat(e.target.value) || 0)}
            placeholder={field.description || `Enter ${field.name.toLowerCase()}`}
            disabled={!editing}
          />
        );
      
      case 'boolean':
        return (
          <Select
            value={value?.toString() || 'false'}
            onChange={(e) => updateFieldValue(field.id, e.target.value === 'true')}
            disabled={!editing}
          >
            <option value="true">Yes</option>
            <option value="false">No</option>
          </Select>
        );
      
      case 'tags':
        return (
          <div className="space-y-2">
            <div className="flex space-x-2">
              <Input
                value={newTag}
                onChange={(e) => setNewTag(e.target.value)}
                placeholder="Add tag"
                disabled={!editing}
                onKeyPress={(e) => e.key === 'Enter' && addTag()}
              />
              {editing && (
                <Button size="sm" onClick={addTag}>Add</Button>
              )}
            </div>
            <div className="flex flex-wrap gap-1">
              {Array.isArray(value) ? value.map((tag, index) => (
                <Badge key={index} variant="secondary" className="flex items-center space-x-1">
                  <span>{tag}</span>
                  {editing && (
                    <button
                      onClick={() => updateFieldValue(field.id, value.filter((_, i) => i !== index))}
                      className="ml-1 text-xs hover:text-red-500"
                    >
                      ×
                    </button>
                  )}
                </Badge>
              )) : null}
            </div>
          </div>
        );
      
      default:
        return (
          <Input
            value={value || ''}
            onChange={(e) => updateFieldValue(field.id, e.target.value)}
            placeholder={`Enter ${field.name.toLowerCase()}`}
            disabled={!editing}
          />
        );
    }
  };

  if (loading) {
    return (
      <Card>
        <CardContent className="p-4">
          <div className="animate-pulse space-y-4">
            <div className="h-4 bg-gray-200 rounded w-3/4"></div>
            <div className="h-4 bg-gray-200 rounded w-1/2"></div>
            <div className="h-4 bg-gray-200 rounded w-5/6"></div>
          </div>
        </CardContent>
      </Card>
    );
  }

  if (!context) {
    return (
      <Card>
        <CardContent className="p-4 text-center text-gray-500">
          No context available for this conversation
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader className="pb-3">
          <div className="flex justify-between items-center">
            <CardTitle className="text-lg">Conversation Context</CardTitle>
            <div className="space-x-2">
              {editing ? (
                <>
                  <Button size="sm" variant="outline" onClick={() => setEditing(false)}>
                    Cancel
                  </Button>
                  <Button size="sm" onClick={handleSave}>
                    Save
                  </Button>
                </>
              ) : (
                <Button size="sm" onClick={() => setEditing(true)}>
                  Edit
                </Button>
              )}
            </div>
          </div>
        </CardHeader>
        <CardContent className="space-y-4">
          {/* Status and Priority */}
          <div className="grid grid-cols-2 gap-4">
            <div>
              <Label>Status</Label>
                             {editing ? (
                 <Select value={context.status} onChange={(e) => updateStatus(e.target.value)}>
                   {context.schema.status_workflow.statuses.map(status => (
                     <option key={status.id} value={status.id}>
                       {status.label}
                     </option>
                   ))}
                 </Select>
               ) : (
                <div className="flex items-center space-x-2 p-2 bg-gray-50 rounded">
                  <div className={`w-3 h-3 rounded-full bg-${context.schema.status_workflow.statuses.find(s => s.id === context.status)?.color || 'gray'}-500`}></div>
                  <span>{context.schema.status_workflow.statuses.find(s => s.id === context.status)?.label || context.status}</span>
                </div>
              )}
            </div>
            
            <div>
              <Label>Priority</Label>
              {editing ? (
                <Select value={context.priority} onChange={(e) => updatePriority(e.target.value)}>
                  <option value="low">Low</option>
                  <option value="medium">Medium</option>
                  <option value="high">High</option>
                  <option value="critical">Critical</option>
                </Select>
              ) : (
                <div className={`p-2 rounded text-center font-medium ${
                  context.priority === 'critical' ? 'bg-red-100 text-red-800' :
                  context.priority === 'high' ? 'bg-orange-100 text-orange-800' :
                  context.priority === 'medium' ? 'bg-yellow-100 text-yellow-800' :
                  'bg-green-100 text-green-800'
                }`}>
                  {context.priority.charAt(0).toUpperCase() + context.priority.slice(1)}
                </div>
              )}
            </div>
          </div>

          {/* Tags */}
          <div>
            <Label>Tags</Label>
            <div className="flex flex-wrap gap-1 mt-1">
              {context.tags.map((tag, index) => (
                <Badge key={index} variant="secondary" className="flex items-center space-x-1">
                  <span>{tag}</span>
                  {editing && (
                    <button
                      onClick={() => removeTag(tag)}
                      className="ml-1 text-xs hover:text-red-500"
                    >
                      ×
                    </button>
                  )}
                </Badge>
              ))}
            </div>
            {editing && (
              <div className="flex space-x-2 mt-2">
                <Input
                  value={newTag}
                  onChange={(e) => setNewTag(e.target.value)}
                  placeholder="Add new tag"
                  onKeyPress={(e) => e.key === 'Enter' && addTag()}
                />
                <Button size="sm" onClick={addTag}>Add</Button>
              </div>
            )}
          </div>

          {/* Context Fields */}
          <div className="space-y-4">
            <Label>Context Fields</Label>
            {context.schema.fields.map(field => (
              <div key={field.id} className="space-y-2">
                <Label className="text-sm font-medium">
                  {field.name}
                  {field.required && <span className="text-red-500 ml-1">*</span>}
                </Label>
                {renderFieldInput(field)}
                {field.description && (
                  <p className="text-xs text-gray-500">{field.description}</p>
                )}
              </div>
            ))}
          </div>

          {/* Last Updated */}
          <div className="text-xs text-gray-500 pt-2 border-t">
            Last updated: {new Date(context.last_updated).toLocaleString()}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

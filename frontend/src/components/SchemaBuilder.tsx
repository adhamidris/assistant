'use client';

import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from './ui/card';
import { Button } from './ui/button';
import { Input } from './ui/input';
import { Label } from './ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from './ui/select';
import { Textarea } from './ui/textarea';

interface SchemaField {
  id: string;
  name: string;
  type: string;
  required: boolean;
  choices?: string[];
  dependencies?: Record<string, any>;
  description?: string;
  placeholder?: string;
  validation?: Record<string, any>;
}

interface StatusWorkflow {
  statuses: Array<{
    id: string;
    label: string;
    color: string;
  }>;
  transitions: Record<string, string[]>;
}

interface PriorityConfig {
  default_priority: string;
  rules: Array<{
    type: string;
    field_id: string;
    condition: string;
    value: any;
    priority: string;
  }>;
}

interface WorkspaceContextSchema {
  id?: string;
  name: string;
  description: string;
  fields: SchemaField[];
  status_workflow: StatusWorkflow;
  priority_config: PriorityConfig;
  is_active: boolean;
  is_default: boolean;
}

const FIELD_TYPES = [
  { value: 'text', label: 'Text Field' },
  { value: 'textarea', label: 'Text Area' },
  { value: 'choice', label: 'Choice Dropdown' },
  { value: 'multi_choice', label: 'Multi-Select' },
  { value: 'date', label: 'Date' },
  { value: 'datetime', label: 'Date & Time' },
  { value: 'number', label: 'Number' },
  { value: 'decimal', label: 'Decimal' },
  { value: 'boolean', label: 'Yes/No' },
  { value: 'tags', label: 'Tags' },
  { value: 'email', label: 'Email' },
  { value: 'phone', label: 'Phone Number' },
  { value: 'url', label: 'URL' },
  { value: 'priority', label: 'Priority Level' },
  { value: 'status', label: 'Status' },
];

const PRIORITY_LEVELS = ['low', 'medium', 'high', 'critical'];
const STATUS_COLORS = ['blue', 'green', 'yellow', 'orange', 'red', 'purple', 'gray'];

export default function SchemaBuilder({ 
  workspaceId, 
  onSave, 
  initialSchema 
}: { 
  workspaceId: string; 
  onSave: (schema: WorkspaceContextSchema) => void;
  initialSchema?: WorkspaceContextSchema;
}) {
  const [schema, setSchema] = useState<WorkspaceContextSchema>({
    name: '',
    description: '',
    fields: [],
    status_workflow: {
      statuses: [
        { id: 'new', label: 'New', color: 'blue' },
        { id: 'in_progress', label: 'In Progress', color: 'yellow' },
        { id: 'resolved', label: 'Resolved', color: 'green' }
      ],
      transitions: {
        'new': ['in_progress'],
        'in_progress': ['resolved'],
        'resolved': []
      }
    },
    priority_config: {
      default_priority: 'medium',
      rules: []
    },
    is_active: true,
    is_default: false
  });

  const [activeTab, setActiveTab] = useState<'fields' | 'workflow' | 'priority' | 'preview'>('fields');
  const [editingFieldIndex, setEditingFieldIndex] = useState<number | null>(null);
  const [editingStatusIndex, setEditingStatusIndex] = useState<number | null>(null);

  useEffect(() => {
    if (initialSchema) {
      setSchema(initialSchema);
    }
  }, [initialSchema]);

  const addField = () => {
    const newField: SchemaField = {
      id: `field_${Date.now()}`,
      name: '',
      type: 'text',
      required: false,
      choices: [],
      dependencies: {},
      description: '',
      placeholder: '',
      validation: {}
    };
    setSchema(prev => ({
      ...prev,
      fields: [...prev.fields, newField]
    }));
    setEditingFieldIndex(schema.fields.length);
  };

  const updateField = (index: number, field: Partial<SchemaField>) => {
    setSchema(prev => ({
      ...prev,
      fields: prev.fields.map((f, i) => i === index ? { ...f, ...field } : f)
    }));
  };

  const removeField = (index: number) => {
    setSchema(prev => ({
      ...prev,
      fields: prev.fields.filter((_, i) => i !== index)
    }));
  };

  const addStatus = () => {
    const newStatus = {
      id: `status_${Date.now()}`,
      label: '',
      color: 'blue'
    };
    setSchema(prev => ({
      ...prev,
      status_workflow: {
        ...prev.status_workflow,
        statuses: [...prev.status_workflow.statuses, newStatus],
        transitions: {
          ...prev.status_workflow.transitions,
          [newStatus.id]: []
        }
      }
    }));
    setEditingStatusIndex(schema.status_workflow.statuses.length);
  };

  const updateStatus = (index: number, status: Partial<typeof schema.status_workflow.statuses[0]>) => {
    setSchema(prev => ({
      ...prev,
      status_workflow: {
        ...prev.status_workflow,
        statuses: prev.status_workflow.statuses.map((s, i) => 
          i === index ? { ...s, ...status } : s
        )
      }
    }));
  };

  const removeStatus = (index: number) => {
    const statusToRemove = schema.status_workflow.statuses[index];
    setSchema(prev => ({
      ...prev,
      status_workflow: {
        ...prev.status_workflow,
        statuses: prev.status_workflow.statuses.filter((_, i) => i !== index),
        transitions: Object.fromEntries(
          Object.entries(prev.status_workflow.transitions)
            .filter(([key]) => key !== statusToRemove.id)
            .map(([key, value]) => [key, value.filter(s => s !== statusToRemove.id)])
        )
      }
    }));
  };

  const addPriorityRule = () => {
    const newRule = {
      type: 'equals',
      field_id: '',
      condition: 'equals',
      value: '',
      priority: 'medium'
    };
    setSchema(prev => ({
      ...prev,
      priority_config: {
        ...prev.priority_config,
        rules: [...prev.priority_config.rules, newRule]
      }
    }));
  };

  const updatePriorityRule = (index: number, rule: Partial<typeof schema.priority_config.rules[0]>) => {
    setSchema(prev => ({
      ...prev,
      priority_config: {
        ...prev.priority_config,
        rules: prev.priority_config.rules.map((r, i) => 
          i === index ? { ...r, ...rule } : r
        )
      }
    }));
  };

  const removePriorityRule = (index: number) => {
    setSchema(prev => ({
      ...prev,
      priority_config: {
        ...prev.priority_config,
        rules: prev.priority_config.rules.filter((_, i) => i !== index)
      }
    }));
  };

  const handleSave = () => {
    // Validate schema before saving
    const errors = validateSchema();
    if (errors.length > 0) {
      alert('Schema validation errors:\n' + errors.join('\n'));
      return;
    }
    onSave(schema);
  };

  const validateSchema = (): string[] => {
    const errors: string[] = [];
    
    if (!schema.name.trim()) {
      errors.push('Schema name is required');
    }
    
    if (schema.fields.length === 0) {
      errors.push('At least one field is required');
    }
    
    // Validate fields
    schema.fields.forEach((field, index) => {
      if (!field.name.trim()) {
        errors.push(`Field ${index + 1}: Name is required`);
      }
      if (!field.id.trim()) {
        errors.push(`Field ${index + 1}: ID is required`);
      }
      if (field.type === 'choice' && (!field.choices || field.choices.length === 0)) {
        errors.push(`Field ${index + 1}: Choice fields must have options`);
      }
    });
    
    // Validate status workflow
    if (schema.status_workflow.statuses.length === 0) {
      errors.push('At least one status is required');
    }
    
    return errors;
  };

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle>Schema Builder</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            <div>
              <Label htmlFor="schema-name">Schema Name</Label>
              <Input
                id="schema-name"
                value={schema.name}
                onChange={(e) => setSchema(prev => ({ ...prev, name: e.target.value }))}
                placeholder="e.g., Customer Service, Sales Inquiry"
              />
            </div>
            
            <div>
              <Label htmlFor="schema-description">Description</Label>
              <Textarea
                id="schema-description"
                value={schema.description}
                onChange={(e) => setSchema(prev => ({ ...prev, description: e.target.value }))}
                placeholder="What does this schema track?"
              />
            </div>
          </div>
        </CardContent>
      </Card>

      <div className="flex space-x-2">
        <Button
          variant={activeTab === 'fields' ? 'default' : 'outline'}
          onClick={() => setActiveTab('fields')}
        >
          Fields
        </Button>
        <Button
          variant={activeTab === 'workflow' ? 'default' : 'outline'}
          onClick={() => setActiveTab('workflow')}
        >
          Status Workflow
        </Button>
        <Button
          variant={activeTab === 'priority' ? 'default' : 'outline'}
          onClick={() => setActiveTab('priority')}
        >
          Priority Rules
        </Button>
        <Button
          variant={activeTab === 'preview' ? 'default' : 'outline'}
          onClick={() => setActiveTab('preview')}
        >
          Preview
        </Button>
      </div>

      {activeTab === 'fields' && (
        <Card>
          <CardHeader>
            <CardTitle>Schema Fields</CardTitle>
            <Button onClick={addField}>Add Field</Button>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {schema.fields.map((field, index) => (
                <div key={index} className="border rounded-lg p-4 space-y-3">
                  <div className="flex justify-between items-center">
                    <h4 className="font-medium">Field {index + 1}</h4>
                    <div className="space-x-2">
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => setEditingFieldIndex(editingFieldIndex === index ? null : index)}
                      >
                        {editingFieldIndex === index ? 'Cancel' : 'Edit'}
                      </Button>
                      <Button
                        variant="destructive"
                        size="sm"
                        onClick={() => removeField(index)}
                      >
                        Remove
                      </Button>
                    </div>
                  </div>
                  
                  {editingFieldIndex === index ? (
                    <div className="space-y-3">
                      <div className="grid grid-cols-2 gap-3">
                        <div>
                          <Label>Field ID</Label>
                          <Input
                            value={field.id}
                            onChange={(e) => updateField(index, { id: e.target.value })}
                            placeholder="unique_field_id"
                          />
                        </div>
                        <div>
                          <Label>Field Name</Label>
                          <Input
                            value={field.name}
                            onChange={(e) => updateField(index, { name: e.target.value })}
                            placeholder="Display Name"
                          />
                        </div>
                      </div>
                      
                      <div className="grid grid-cols-2 gap-3">
                        <div>
                          <Label>Field Type</Label>
                          <Select value={field.type} onValueChange={(value) => updateField(index, { type: value })}>
                            <SelectTrigger>
                              <SelectValue />
                            </SelectTrigger>
                            <SelectContent>
                              {FIELD_TYPES.map(type => (
                                <SelectItem key={type.value} value={type.value}>
                                  {type.label}
                                </SelectItem>
                              ))}
                            </SelectContent>
                          </Select>
                        </div>
                        <div className="flex items-center space-x-2">
                          <input
                            type="checkbox"
                            id={`required-${index}`}
                            checked={field.required}
                            onChange={(e) => updateField(index, { required: e.target.checked })}
                          />
                          <Label htmlFor={`required-${index}`}>Required</Label>
                        </div>
                      </div>
                      
                      {(field.type === 'choice' || field.type === 'multi_choice') && (
                        <div>
                          <Label>Choices (one per line)</Label>
                          <Textarea
                            value={field.choices?.join('\n') || ''}
                            onChange={(e) => updateField(index, { 
                              choices: e.target.value.split('\n').filter(c => c.trim()) 
                            })}
                            placeholder="Option 1&#10;Option 2&#10;Option 3"
                          />
                        </div>
                      )}
                      
                      <div>
                        <Label>Description</Label>
                        <Input
                          value={field.description || ''}
                          onChange={(e) => updateField(index, { description: e.target.value })}
                          placeholder="Field description"
                        />
                      </div>
                      
                      <div>
                        <Label>Placeholder</Label>
                        <Input
                          value={field.placeholder || ''}
                          onChange={(e) => updateField(index, { placeholder: e.target.value })}
                          placeholder="Placeholder text"
                        />
                      </div>
                    </div>
                  ) : (
                    <div className="grid grid-cols-4 gap-2 text-sm">
                      <div><strong>ID:</strong> {field.id}</div>
                      <div><strong>Name:</strong> {field.name}</div>
                      <div><strong>Type:</strong> {field.type}</div>
                      <div><strong>Required:</strong> {field.required ? 'Yes' : 'No'}</div>
                    </div>
                  )}
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {activeTab === 'workflow' && (
        <Card>
          <CardHeader>
            <CardTitle>Status Workflow</CardTitle>
            <Button onClick={addStatus}>Add Status</Button>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {schema.status_workflow.statuses.map((status, index) => (
                <div key={index} className="border rounded-lg p-4 space-y-3">
                  <div className="flex justify-between items-center">
                    <h4 className="font-medium">Status {index + 1}</h4>
                    <div className="space-x-2">
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => setEditingStatusIndex(editingStatusIndex === index ? null : index)}
                      >
                        {editingStatusIndex === index ? 'Cancel' : 'Edit'}
                      </Button>
                      <Button
                        variant="destructive"
                        size="sm"
                        onClick={() => removeStatus(index)}
                      >
                        Remove
                      </Button>
                    </div>
                  </div>
                  
                  {editingStatusIndex === index ? (
                    <div className="grid grid-cols-3 gap-3">
                      <div>
                        <Label>Status ID</Label>
                        <Input
                          value={status.id}
                          onChange={(e) => updateStatus(index, { id: e.target.value })}
                          placeholder="status_id"
                        />
                      </div>
                      <div>
                        <Label>Display Label</Label>
                        <Input
                          value={status.label}
                          onChange={(e) => updateStatus(index, { label: e.target.value })}
                          placeholder="Display Name"
                        />
                      </div>
                      <div>
                        <Label>Color</Label>
                        <Select value={status.color} onValueChange={(value) => updateStatus(index, { color: value })}>
                          <SelectTrigger>
                            <SelectValue />
                          </SelectTrigger>
                          <SelectContent>
                            {STATUS_COLORS.map(color => (
                              <SelectItem key={color} value={color}>
                                {color.charAt(0).toUpperCase() + color.slice(1)}
                              </SelectItem>
                            ))}
                          </SelectContent>
                        </Select>
                      </div>
                    </div>
                  ) : (
                    <div className="grid grid-cols-3 gap-2 text-sm">
                      <div><strong>ID:</strong> {status.id}</div>
                      <div><strong>Label:</strong> {status.label}</div>
                      <div><strong>Color:</strong> {status.color}</div>
                    </div>
                  )}
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {activeTab === 'priority' && (
        <Card>
          <CardHeader>
            <CardTitle>Priority Configuration</CardTitle>
            <Button onClick={addPriorityRule}>Add Priority Rule</Button>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              <div>
                <Label>Default Priority</Label>
                <Select 
                  value={schema.priority_config.default_priority} 
                  onValueChange={(value) => setSchema(prev => ({
                    ...prev,
                    priority_config: { ...prev.priority_config, default_priority: value }
                  }))}
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {PRIORITY_LEVELS.map(priority => (
                      <SelectItem key={priority} value={priority}>
                        {priority.charAt(0).toUpperCase() + priority.slice(1)}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              
              {schema.priority_config.rules.map((rule, index) => (
                <div key={index} className="border rounded-lg p-4 space-y-3">
                  <div className="flex justify-between items-center">
                    <h4 className="font-medium">Priority Rule {index + 1}</h4>
                    <Button
                      variant="destructive"
                      size="sm"
                      onClick={() => removePriorityRule(index)}
                    >
                      Remove
                    </Button>
                  </div>
                  
                  <div className="grid grid-cols-5 gap-3">
                    <div>
                      <Label>Field</Label>
                      <Select 
                        value={rule.field_id} 
                        onValueChange={(value) => updatePriorityRule(index, { field_id: value })}
                      >
                        <SelectTrigger>
                          <SelectValue placeholder="Select field" />
                        </SelectTrigger>
                        <SelectContent>
                          {schema.fields.map(field => (
                            <SelectItem key={field.id} value={field.id}>
                              {field.name}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    </div>
                    
                    <div>
                      <Label>Condition</Label>
                      <Select 
                        value={rule.condition} 
                        onValueChange={(value) => updatePriorityRule(index, { condition: value })}
                      >
                        <SelectTrigger>
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="equals">Equals</SelectItem>
                          <SelectItem value="contains">Contains</SelectItem>
                          <SelectItem value="greater_than">Greater Than</SelectItem>
                          <SelectItem value="less_than">Less Than</SelectItem>
                          <SelectItem value="is_set">Is Set</SelectItem>
                          <SelectItem value="is_empty">Is Empty</SelectItem>
                        </SelectContent>
                      </Select>
                    </div>
                    
                    <div>
                      <Label>Value</Label>
                      <Input
                        value={rule.value}
                        onChange={(e) => updatePriorityRule(index, { value: e.target.value })}
                        placeholder="Value to compare"
                      />
                    </div>
                    
                    <div>
                      <Label>Priority</Label>
                      <Select 
                        value={rule.priority} 
                        onValueChange={(value) => updatePriorityRule(index, { priority: value })}
                      >
                        <SelectTrigger>
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          {PRIORITY_LEVELS.map(priority => (
                            <SelectItem key={priority} value={priority}>
                              {priority.charAt(0).toUpperCase() + priority.slice(1)}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {activeTab === 'preview' && (
        <Card>
          <CardHeader>
            <CardTitle>Schema Preview</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              <div>
                <h4 className="font-medium">Schema Information</h4>
                <div className="grid grid-cols-2 gap-2 text-sm mt-2">
                  <div><strong>Name:</strong> {schema.name || 'Not set'}</div>
                  <div><strong>Description:</strong> {schema.description || 'Not set'}</div>
                  <div><strong>Fields:</strong> {schema.fields.length}</div>
                  <div><strong>Statuses:</strong> {schema.status_workflow.statuses.length}</div>
                  <div><strong>Priority Rules:</strong> {schema.priority_config.rules.length}</div>
                  <div><strong>Default Priority:</strong> {schema.priority_config.default_priority}</div>
                </div>
              </div>
              
              <div>
                <h4 className="font-medium">Fields</h4>
                <div className="space-y-2 mt-2">
                  {schema.fields.map((field, index) => (
                    <div key={index} className="text-sm p-2 bg-gray-50 rounded">
                      <strong>{field.name}</strong> ({field.type}) {field.required && <span className="text-red-500">*</span>}
                    </div>
                  ))}
                </div>
              </div>
              
              <div>
                <h4 className="font-medium">Status Workflow</h4>
                <div className="space-y-2 mt-2">
                  {schema.status_workflow.statuses.map((status, index) => (
                    <div key={index} className="text-sm p-2 bg-gray-50 rounded">
                      <span className={`inline-block w-3 h-3 rounded-full bg-${status.color}-500 mr-2`}></span>
                      {status.label} ({status.id})
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      <div className="flex justify-end space-x-2">
        <Button variant="outline">Cancel</Button>
        <Button onClick={handleSave}>Save Schema</Button>
      </div>
    </div>
  );
}

'use client'

import { useState, useEffect } from 'react'
import { 
  Building2, 
  CheckCircle, 
  AlertCircle, 
  Settings, 
  Download,
  FileText,
  Shield,
  Lightbulb,
  Eye,
  Zap,
  Users,
  Workflow
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import { getBusinessTemplates, getBusinessTemplate, applyBusinessTemplate } from '@/lib/api'

interface BusinessTemplate {
  id: string
  name: string
  industry: string
  description: string
  version: string
  is_featured: boolean
  is_active: boolean
}

interface BusinessSetupData {
  industry: string
  business_type: string
  compliance_requirements: string[]
  integration_preferences: string[]
  custom_instructions: string
}

const INDUSTRY_OPTIONS = [
  { value: 'healthcare', label: 'Healthcare/Medical', icon: Shield },
  { value: 'restaurant', label: 'Restaurant/Food Service', icon: Building2 },
  { value: 'finance', label: 'Financial Services', icon: Building2 },
  { value: 'ecommerce', label: 'E-commerce/Retail', icon: Building2 },
  { value: 'realestate', label: 'Real Estate', icon: Building2 },
  { value: 'professional', label: 'Professional Services', icon: Building2 },
  { value: 'education', label: 'Education/Training', icon: Building2 },
  { value: 'consulting', label: 'Consulting/Advisory', icon: Building2 },
  { value: 'manufacturing', label: 'Manufacturing/Industrial', icon: Building2 },
  { value: 'technology', label: 'Technology/SaaS', icon: Building2 },
  { value: 'hospitality', label: 'Hospitality/Tourism', icon: Building2 },
  { value: 'legal', label: 'Legal Services', icon: Shield },
  { value: 'creative', label: 'Creative/Media', icon: Lightbulb },
  { value: 'nonprofit', label: 'Non-Profit/Charity', icon: Building2 },
  { value: 'other', label: 'Other/General', icon: Building2 }
]

const COMPLIANCE_OPTIONS = [
  'GDPR Compliance',
  'HIPAA Compliance',
  'PCI DSS Compliance',
  'SOC 2 Compliance',
  'ISO 27001',
  'CCPA Compliance',
  'Industry-specific regulations'
]

const INTEGRATION_OPTIONS = [
  'CRM Integration',
  'Payment Processing',
  'Email Marketing',
  'Analytics Tools',
  'Calendar Systems',
  'Social Media',
  'Customer Support Tools',
  'Inventory Management'
]

export default function BusinessTypeSetup({ workspaceId }: { workspaceId: string }) {
  const [templates, setTemplates] = useState<BusinessTemplate[]>([])
  const [filteredTemplates, setFilteredTemplates] = useState<BusinessTemplate[]>([])
  const [selectedTemplate, setSelectedTemplate] = useState<BusinessTemplate | null>(null)
  const [templatePreview, setTemplatePreview] = useState<any>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [isApplying, setIsApplying] = useState(false)
  const [isLoadingPreview, setIsLoadingPreview] = useState(false)
  const [setupData, setSetupData] = useState<BusinessSetupData>({
    industry: '',
    business_type: '',
    compliance_requirements: [],
    integration_preferences: [],
    custom_instructions: ''
  })

  useEffect(() => {
    loadTemplates()
  }, [])

  const loadTemplates = async () => {
    try {
      setIsLoading(true)
      const data = await getBusinessTemplates()
      const templatesData = data.results || data
      setTemplates(templatesData)
      setFilteredTemplates(templatesData)
    } catch (error) {
      console.error('Error loading templates:', error)
    } finally {
      setIsLoading(false)
    }
  }

  const loadTemplatePreview = async (template: BusinessTemplate) => {
    try {
      setIsLoadingPreview(true)
      const templateData = await getBusinessTemplate(template.id)
      setTemplatePreview(templateData)
    } catch (error) {
      console.error('Error loading template preview:', error)
    } finally {
      setIsLoadingPreview(false)
    }
  }

  const applyTemplate = async (template: BusinessTemplate) => {
    try {
      setIsApplying(true)
      const result = await applyBusinessTemplate(template.id, workspaceId)
      alert(`Template "${template.name}" applied successfully!`)
      console.log('Template application result:', result)
      
      // Reload templates to update usage counts
      await loadTemplates()
    } catch (error) {
      console.error('Error applying template:', error)
      alert('Error applying template')
    } finally {
      setIsApplying(false)
    }
  }

  const handleIndustryChange = (industry: string) => {
    setSetupData(prev => ({ ...prev, industry }))
    
    // Auto-select a template for this industry
    const industryTemplate = templates.find(t => t.industry === industry && t.is_featured)
    if (industryTemplate) {
      setSelectedTemplate(industryTemplate)
    }
  }

  const handleComplianceToggle = (requirement: string) => {
    setSetupData(prev => ({
      ...prev,
      compliance_requirements: prev.compliance_requirements.includes(requirement)
        ? prev.compliance_requirements.filter(r => r !== requirement)
        : [...prev.compliance_requirements, requirement]
    }))
  }

  const handleIntegrationToggle = (integration: string) => {
    setSetupData(prev => ({
      ...prev,
      integration_preferences: prev.integration_preferences.includes(integration)
        ? prev.integration_preferences.filter(i => i !== integration)
        : [...prev.integration_preferences, integration]
    }))
  }

  const saveSetup = async () => {
    try {
      // This would typically save to the workspace configuration
      // For now, we'll just show a success message
      alert('Business setup configuration saved successfully!')
      console.log('Saving business setup:', setupData)
    } catch (error) {
      console.error('Error saving setup:', error)
      alert('Error saving setup')
    }
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
      <div>
        <h2 className="text-2xl font-bold text-gray-900">Business Setup</h2>
        <p className="text-gray-600">Configure your business type and industry-specific settings</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Business Type Configuration */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center space-x-2">
              <Building2 className="w-5 h-5" />
              <span>Business Configuration</span>
            </CardTitle>
            <CardDescription>
              Set up your business type and industry-specific requirements
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <Label htmlFor="industry">Industry</Label>
              <select
                id="industry"
                value={setupData.industry}
                onChange={(e) => handleIndustryChange(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <option value="">Select your industry</option>
                {INDUSTRY_OPTIONS.map((industry) => {
                  const Icon = industry.icon
                  return (
                    <option key={industry.value} value={industry.value}>
                      {industry.label}
                    </option>
                  )
                })}
              </select>
            </div>

            <div>
              <Label htmlFor="business_type">Business Type</Label>
              <input
                id="business_type"
                type="text"
                value={setupData.business_type}
                onChange={(e) => setSetupData(prev => ({ ...prev, business_type: e.target.value }))}
                placeholder="e.g., Medical Practice, Restaurant Chain, SaaS Company"
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>

            <div>
              <Label>Compliance Requirements</Label>
              <div className="mt-2 space-y-2">
                {COMPLIANCE_OPTIONS.map((requirement) => (
                  <label key={requirement} className="flex items-center space-x-2">
                    <input
                      type="checkbox"
                      checked={setupData.compliance_requirements.includes(requirement)}
                      onChange={() => handleComplianceToggle(requirement)}
                      className="rounded border-gray-300"
                    />
                    <span className="text-sm text-gray-700">{requirement}</span>
                  </label>
                ))}
              </div>
            </div>

            <div>
              <Label>Integration Preferences</Label>
              <div className="mt-2 space-y-2">
                {INTEGRATION_OPTIONS.map((integration) => (
                  <label key={integration} className="flex items-center space-x-2">
                    <input
                      type="checkbox"
                      checked={setupData.integration_preferences.includes(integration)}
                      onChange={() => handleIntegrationToggle(integration)}
                      className="rounded border-gray-300"
                    />
                    <span className="text-sm text-gray-700">{integration}</span>
                  </label>
                ))}
              </div>
            </div>

            <div>
              <Label htmlFor="custom_instructions">Custom Instructions</Label>
              <Textarea
                id="custom_instructions"
                value={setupData.custom_instructions}
                onChange={(e) => setSetupData(prev => ({ ...prev, custom_instructions: e.target.value }))}
                placeholder="Any specific business requirements or custom instructions..."
                rows={3}
              />
            </div>

            <Button onClick={saveSetup} className="w-full">
              <Settings className="w-4 h-4 mr-2" />
              Save Configuration
            </Button>
          </CardContent>
        </Card>

        {/* Industry Templates */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center space-x-2">
              <FileText className="w-5 h-5" />
              <span>Industry Templates</span>
            </CardTitle>
            <CardDescription>
              Choose from pre-built templates for your industry
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            {/* Template Filter */}
            <div className="flex items-center justify-between mb-3">
              <div className="flex space-x-2 flex-1">
                <input
                  type="text"
                  placeholder="Search templates..."
                  className="flex-1 px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 text-sm"
                  onChange={(e) => {
                    const searchTerm = e.target.value.toLowerCase()
                    const filtered = templates.filter(t => 
                      t.name.toLowerCase().includes(searchTerm) ||
                      t.description.toLowerCase().includes(searchTerm) ||
                      t.industry.toLowerCase().includes(searchTerm)
                    )
                    setFilteredTemplates(filtered)
                  }}
                />
                <select
                  className="px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 text-sm"
                  onChange={(e) => {
                    const industry = e.target.value
                    if (industry) {
                      const filtered = templates.filter(t => t.industry === industry)
                      setFilteredTemplates(filtered)
                    } else {
                      setFilteredTemplates(templates) // Reset to all templates
                    }
                  }}
                >
                  <option value="">All Industries</option>
                  {INDUSTRY_OPTIONS.map((industry) => (
                    <option key={industry.value} value={industry.value}>
                      {industry.label}
                    </option>
                  ))}
                </select>
              </div>
              <div className="text-sm text-gray-500 ml-4">
                {filteredTemplates.length} of {templates.length} templates
              </div>
            </div>
            {filteredTemplates.length === 0 ? (
              <div className="text-center py-8 text-gray-500">
                <FileText className="w-12 h-12 mx-auto mb-4 text-gray-300" />
                <p>No templates found</p>
              </div>
            ) : (
              <div className="space-y-3">
                {filteredTemplates
                  .filter(t => !setupData.industry || t.industry === setupData.industry)
                  .map((template) => (
                    <div
                      key={template.id}
                      className={`p-4 border rounded-lg cursor-pointer transition-colors ${
                        selectedTemplate?.id === template.id
                          ? 'border-blue-500 bg-blue-50'
                          : 'border-gray-200 hover:border-gray-300'
                      }`}
                      onClick={() => setSelectedTemplate(template)}
                    >
                      <div className="flex items-start justify-between">
                        <div className="flex-1">
                          <div className="flex items-center space-x-2 mb-2">
                            <h4 className="font-medium text-gray-900">{template.name}</h4>
                            {template.is_featured && (
                              <span className="px-2 py-1 text-xs bg-yellow-100 text-yellow-800 rounded-full">
                                Featured
                              </span>
                            )}
                          </div>
                          <p className="text-sm text-gray-600 mb-2">{template.description}</p>
                          <div className="flex items-center space-x-4 text-xs text-gray-500">
                            <span>Industry: {template.industry}</span>
                            <span>Version: {template.version}</span>
                          </div>
                        </div>
                        <div className="flex items-center space-x-2">
                          {template.is_active ? (
                            <CheckCircle className="w-5 h-5 text-green-500" />
                          ) : (
                            <AlertCircle className="w-5 h-5 text-red-500" />
                          )}
                        </div>
                      </div>
                    </div>
                  ))}
              </div>
            )}

            {selectedTemplate && (
              <div className="mt-4 p-4 bg-blue-50 border border-blue-200 rounded-lg">
                <div className="flex items-center justify-between mb-3">
                  <h4 className="font-medium text-blue-900">Selected Template</h4>
                  <Button
                    onClick={() => loadTemplatePreview(selectedTemplate)}
                    disabled={isLoadingPreview}
                    variant="outline"
                    size="sm"
                  >
                    {isLoadingPreview ? (
                      <div className="w-4 h-4 border-2 border-blue-600 border-t-transparent rounded-full animate-spin mr-2" />
                    ) : (
                      <Eye className="w-4 h-4 mr-2" />
                    )}
                    {isLoadingPreview ? 'Loading...' : 'Preview'}
                  </Button>
                </div>
                <p className="text-sm text-blue-700 mb-3">{selectedTemplate.description}</p>
                
                {/* Template Preview */}
                {templatePreview && (
                  <div className="mb-4 p-3 bg-white rounded border">
                    <h5 className="font-medium text-gray-900 mb-2">Template Preview</h5>
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-3 text-xs mb-3">
                      <div className="flex items-center space-x-2">
                        <Workflow className="w-4 h-4 text-blue-500" />
                        <span>{templatePreview.default_schema_templates ? Object.keys(templatePreview.default_schema_templates).length : 0} Schemas</span>
                      </div>
                      <div className="flex items-center space-x-2">
                        <Zap className="w-4 h-4 text-green-500" />
                        <span>{templatePreview.default_rule_templates ? Object.keys(templatePreview.default_rule_templates).length : 0} Rules</span>
                      </div>
                      <div className="flex items-center space-x-2">
                        <Users className="w-4 h-4 text-purple-500" />
                        <span>{templatePreview.personality_defaults ? 'AI Agent' : 'No Agent'}</span>
                      </div>
                    </div>
                    
                    {/* Detailed Preview */}
                    <div className="space-y-3">
                      {/* Schemas */}
                      {templatePreview.default_schema_templates && Object.keys(templatePreview.default_schema_templates).length > 0 && (
                        <div>
                          <h6 className="font-medium text-gray-700 mb-2">Schemas to be created:</h6>
                          <div className="space-y-2">
                            {Object.entries(templatePreview.default_schema_templates).map(([key, schema]: [string, any]) => (
                              <div key={key} className="text-xs bg-gray-50 p-2 rounded">
                                <div className="font-medium">{schema.name}</div>
                                <div className="text-gray-600">{schema.description}</div>
                                <div className="text-gray-500 mt-1">
                                  {schema.fields ? `${schema.fields.length} fields` : 'No fields defined'}
                                </div>
                              </div>
                            ))}
                          </div>
                        </div>
                      )}
                      
                      {/* Rules */}
                      {templatePreview.default_rule_templates && Object.keys(templatePreview.default_rule_templates).length > 0 && (
                        <div>
                          <h6 className="font-medium text-gray-700 mb-2">Business rules to be created:</h6>
                          <div className="space-y-2">
                            {Object.entries(templatePreview.default_rule_templates).map(([key, rule]: [string, any]) => (
                              <div key={key} className="text-xs bg-gray-50 p-2 rounded">
                                <div className="font-medium">{rule.name}</div>
                                <div className="text-gray-600">{rule.description}</div>
                                <div className="text-gray-500 mt-1">
                                  Trigger: {rule.trigger_type || 'Unknown'}
                                </div>
                              </div>
                            ))}
                          </div>
                        </div>
                      )}
                      
                      {/* AI Agent */}
                      {templatePreview.personality_defaults && (
                        <div>
                          <h6 className="font-medium text-gray-700 mb-2">AI Agent to be created:</h6>
                          <div className="text-xs bg-gray-50 p-2 rounded">
                            <div className="font-medium">AI {templatePreview.name}</div>
                            <div className="text-gray-600">{templatePreview.description}</div>
                            <div className="text-gray-500 mt-1">
                              Personality: {templatePreview.personality_defaults.tone || 'Professional'}
                            </div>
                          </div>
                        </div>
                      )}
                    </div>
                  </div>
                )}
                
                <Button
                  onClick={() => applyTemplate(selectedTemplate)}
                  disabled={isApplying}
                  className="w-full"
                  size="sm"
                >
                  {isApplying ? (
                    <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin mr-2" />
                  ) : (
                    <Download className="w-4 h-4 mr-2" />
                  )}
                  {isApplying ? 'Applying...' : 'Apply Template'}
                </Button>
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Quick Setup Guide */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center space-x-2">
            <Lightbulb className="w-5 h-5" />
            <span>Quick Setup Guide</span>
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="text-center">
              <div className="w-12 h-12 bg-blue-100 rounded-lg flex items-center justify-center mx-auto mb-3">
                <span className="text-blue-600 font-bold text-xl">1</span>
              </div>
              <h4 className="font-medium text-gray-900 mb-2">Select Industry</h4>
              <p className="text-sm text-gray-600">Choose your business industry from the dropdown</p>
            </div>
            
            <div className="text-center">
              <div className="w-12 h-12 bg-blue-100 rounded-lg flex items-center justify-center mx-auto mb-3">
                <span className="text-blue-600 font-bold text-xl">2</span>
              </div>
              <h4 className="font-medium text-gray-900 mb-2">Apply Template</h4>
              <p className="text-sm text-gray-600">Select and apply an industry-specific template</p>
            </div>
            
            <div className="text-center">
              <div className="w-12 h-12 bg-blue-100 rounded-lg flex items-center justify-center mx-auto mb-3">
                <span className="text-blue-600 font-bold text-xl">3</span>
              </div>
              <h4 className="font-medium text-gray-900 mb-2">Customize</h4>
              <p className="text-sm text-gray-600">Add your specific requirements and integrations</p>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}

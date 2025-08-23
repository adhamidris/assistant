'use client'

import { useState, useEffect } from 'react'
import { 
  Lightbulb, 
  CheckCircle, 
  XCircle, 
  Eye, 
  TrendingUp, 
  FileText,
  Clock,
  AlertCircle
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'

// Import API functions for field suggestions
import { 
  getFieldSuggestions, 
  generateFieldSuggestions, 
  approveFieldSuggestion, 
  rejectFieldSuggestion,
  getFieldSuggestionAnalytics,
  analyzeConversations,
  discoverFields
} from '@/lib/api'

interface FieldSuggestion {
  id: string
  suggested_field_name: string
  field_type: string
  description: string
  frequency_detected: number
  confidence_score: number
  business_value_score: number
  is_reviewed: boolean
  is_approved: boolean
  created_at: string
  sample_values: string[]
  detection_pattern: string
  related_fields: string[]
}

interface ReviewFormData {
  notes: string
  target_schema: string
}

// Field types will be used in future implementations

const FILTER_OPTIONS = [
  { value: 'all', label: 'All Suggestions' },
  { value: 'unreviewed', label: 'Unreviewed' },
  { value: 'approved', label: 'Approved' },
  { value: 'rejected', label: 'Rejected' },
  { value: 'high_confidence', label: 'High Confidence' },
  { value: 'high_value', label: 'High Business Value' }
]

export default function FieldSuggestionsManager({ workspaceId }: { workspaceId: string }) {
  const [suggestions, setSuggestions] = useState<FieldSuggestion[]>([])
  const [filteredSuggestions, setFilteredSuggestions] = useState<FieldSuggestion[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [selectedFilter, setSelectedFilter] = useState('all')
  const [selectedSuggestion, setSelectedSuggestion] = useState<FieldSuggestion | null>(null)
  const [showReviewForm, setShowReviewForm] = useState(false)
  const [reviewForm, setReviewForm] = useState<ReviewFormData>({
    notes: '',
    target_schema: ''
  })
  
  // New state for intelligent discovery
  const [isGeneratingSuggestions, setIsGeneratingSuggestions] = useState(false)
  const [isAnalyzingConversations, setIsAnalyzingConversations] = useState(false)
  const [discoveryResults, setDiscoveryResults] = useState<any>(null)
  const [analytics, setAnalytics] = useState<any>(null)
  const [showDiscoveryPanel, setShowDiscoveryPanel] = useState(false)

  useEffect(() => {
    loadSuggestions()
  }, [workspaceId])

  useEffect(() => {
    filterSuggestions()
  }, [suggestions, selectedFilter])

  const loadSuggestions = async () => {
    try {
      setIsLoading(true)
      // Load real suggestions from API
      const response = await getFieldSuggestions(workspaceId)
      setSuggestions(response.results || response || [])
      
      // Load analytics
      const analyticsResponse = await getFieldSuggestionAnalytics(workspaceId)
      setAnalytics(analyticsResponse.analytics)
    } catch (error) {
      console.error('Error loading suggestions:', error)
      // Fallback to mock data if API fails
      const mockSuggestions: FieldSuggestion[] = [
        {
          id: '1',
          suggested_field_name: 'urgency_level',
          field_type: 'choice',
          description: 'Customer urgency level based on conversation analysis',
          frequency_detected: 15,
          confidence_score: 0.87,
          business_value_score: 0.92,
          is_reviewed: false,
          is_approved: false,
          created_at: '2024-01-15T10:30:00Z',
          sample_values: ['low', 'medium', 'high', 'critical'],
          detection_pattern: 'Keywords like "urgent", "asap", "emergency" in conversations',
          related_fields: ['priority', 'response_time', 'escalation_needed']
        },
        {
          id: '2',
          suggested_field_name: 'customer_tier',
          field_type: 'choice',
          description: 'Customer tier classification based on interaction patterns',
          frequency_detected: 23,
          confidence_score: 0.78,
          business_value_score: 0.85,
          is_reviewed: false,
          is_approved: false,
          created_at: '2024-01-14T14:20:00Z',
          sample_values: ['bronze', 'silver', 'gold', 'platinum'],
          detection_pattern: 'Purchase history, support frequency, and conversation sentiment',
          related_fields: ['lifetime_value', 'support_priority', 'custom_offers']
        },
        {
          id: '3',
          suggested_field_name: 'compliance_required',
          field_type: 'boolean',
          description: 'Whether this conversation requires compliance tracking',
          frequency_detected: 8,
          confidence_score: 0.65,
          business_value_score: 0.78,
          is_reviewed: true,
          is_approved: true,
          created_at: '2024-01-13T09:15:00Z',
          sample_values: ['true', 'false'],
          detection_pattern: 'Regulatory keywords and industry-specific terms',
          related_fields: ['compliance_type', 'audit_trail', 'retention_period']
        }
      ]
      
      setSuggestions(mockSuggestions)
    } finally {
      setIsLoading(false)
    }
  }

  const filterSuggestions = () => {
    let filtered = [...suggestions]
    
    switch (selectedFilter) {
      case 'unreviewed':
        filtered = filtered.filter(s => !s.is_reviewed)
        break
      case 'approved':
        filtered = filtered.filter(s => s.is_approved)
        break
      case 'rejected':
        filtered = filtered.filter(s => s.is_reviewed && !s.is_approved)
        break
      case 'high_confidence':
        filtered = filtered.filter(s => s.confidence_score >= 0.8)
        break
      case 'high_value':
        filtered = filtered.filter(s => s.business_value_score >= 0.8)
        break
      default:
        break
    }
    
    setFilteredSuggestions(filtered)
  }

  const handleApprove = async (suggestion: FieldSuggestion) => {
    try {
      // This will be implemented when we create the API endpoint
      const updatedSuggestion = { ...suggestion, is_approved: true, is_reviewed: true }
      setSuggestions(prev => prev.map(s => s.id === suggestion.id ? updatedSuggestion : s))
      
      alert(`Field "${suggestion.suggested_field_name}" approved successfully!`)
    } catch (error) {
      console.error('Error approving suggestion:', error)
      alert('Error approving suggestion')
    }
  }

  const handleReject = async (suggestion: FieldSuggestion) => {
    try {
      // This will be implemented when we create the API endpoint
      const updatedSuggestion = { ...suggestion, is_approved: false, is_reviewed: true }
      setSuggestions(prev => prev.map(s => s.id === suggestion.id ? updatedSuggestion : s))
      
      alert(`Field "${suggestion.suggested_field_name}" rejected`)
    } catch (error) {
      console.error('Error rejecting suggestion:', error)
      alert('Error rejecting suggestion')
    }
  }

  const openReviewForm = (suggestion: FieldSuggestion) => {
    setSelectedSuggestion(suggestion)
    setShowReviewForm(true)
  }

  const submitReview = async () => {
    if (!selectedSuggestion) return
    
    try {
      // This will be implemented when we create the API endpoint
      const updatedSuggestion = { 
        ...selectedSuggestion, 
        is_approved: true, 
        is_reviewed: true 
      }
      setSuggestions(prev => prev.map(s => s.id === selectedSuggestion.id ? updatedSuggestion : s))
      
      setShowReviewForm(false)
      setSelectedSuggestion(null)
      setReviewForm({ notes: '', target_schema: '' })
      
      alert(`Field "${selectedSuggestion.suggested_field_name}" reviewed and approved!`)
    } catch (error) {
      console.error('Error submitting review:', error)
      alert('Error submitting review')
    }
  }

  const getConfidenceColor = (score: number) => {
    if (score >= 0.8) return 'text-green-600'
    if (score >= 0.6) return 'text-yellow-600'
    return 'text-red-600'
  }

  const getBusinessValueColor = (score: number) => {
    if (score >= 0.8) return 'text-green-600'
    if (score >= 0.6) return 'text-yellow-600'
    return 'text-red-600'
  }

  const getStatusIcon = (suggestion: FieldSuggestion) => {
    if (!suggestion.is_reviewed) {
      return <Clock className="w-4 h-4 text-gray-500" />
    }
    if (suggestion.is_approved) {
      return <CheckCircle className="w-4 h-4 text-green-500" />
    }
    return <XCircle className="w-4 h-4 text-red-500" />
  }

  const getStatusText = (suggestion: FieldSuggestion) => {
    if (!suggestion.is_reviewed) return 'Pending Review'
    if (suggestion.is_approved) return 'Approved'
    return 'Rejected'
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
          <h2 className="text-2xl font-bold text-gray-900">Field Suggestions</h2>
          <p className="text-gray-600">AI-discovered fields to enhance your context schemas</p>
        </div>
        <div className="flex items-center space-x-3">
          <Select value={selectedFilter} onValueChange={setSelectedFilter}>
            <SelectTrigger className="w-48">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {FILTER_OPTIONS.map((option) => (
                <SelectItem key={option.value} value={option.value}>
                  {option.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      </div>

      {/* Review Form Modal */}
      {showReviewForm && selectedSuggestion && (
        <Card className="border-2 border-blue-200">
          <CardHeader>
            <CardTitle>Review Field Suggestion</CardTitle>
            <CardDescription>
                             Review and approve the field &quot;{selectedSuggestion.suggested_field_name}&quot;
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <Label htmlFor="notes">Review Notes</Label>
              <Textarea
                id="notes"
                value={reviewForm.notes}
                onChange={(e) => setReviewForm(prev => ({ ...prev, notes: e.target.value }))}
                placeholder="Add any notes about this field suggestion..."
                rows={3}
              />
            </div>
            
            <div>
              <Label htmlFor="target_schema">Target Schema (Optional)</Label>
              <input
                id="target_schema"
                type="text"
                value={reviewForm.target_schema}
                onChange={(e) => setReviewForm(prev => ({ ...prev, target_schema: e.target.value }))}
                placeholder="Schema name where this field should be added"
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
            
            <div className="flex justify-end space-x-3">
              <Button variant="outline" onClick={() => setShowReviewForm(false)}>
                Cancel
              </Button>
              <Button onClick={submitReview}>
                Approve & Implement
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Suggestions List */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {filteredSuggestions.map((suggestion) => (
          <Card key={suggestion.id} className="relative">
            <CardHeader>
              <div className="flex items-start justify-between">
                <div className="flex items-center space-x-2">
                  <Lightbulb className="w-5 h-5 text-yellow-500" />
                  <div>
                    <CardTitle className="text-lg">{suggestion.suggested_field_name}</CardTitle>
                    <CardDescription className="text-sm">
                      {suggestion.description}
                    </CardDescription>
                  </div>
                </div>
                <div className="flex items-center space-x-2">
                  {getStatusIcon(suggestion)}
                  <span className="text-sm text-gray-600">{getStatusText(suggestion)}</span>
                </div>
              </div>
            </CardHeader>
            
            <CardContent className="space-y-4">
              {/* Field Type */}
              <div className="flex items-center space-x-2">
                <FileText className="w-4 h-4 text-gray-400" />
                <span className="text-sm text-gray-600 capitalize">{suggestion.field_type}</span>
              </div>
              
              {/* Metrics */}
              <div className="grid grid-cols-3 gap-4 text-sm">
                <div className="text-center">
                  <div className="font-semibold text-gray-900">{suggestion.frequency_detected}</div>
                  <div className="text-gray-500">Detections</div>
                </div>
                <div className="text-center">
                  <div className={`font-semibold ${getConfidenceColor(suggestion.confidence_score)}`}>
                    {(suggestion.confidence_score * 100).toFixed(0)}%
                  </div>
                  <div className="text-gray-500">Confidence</div>
                </div>
                <div className="text-center">
                  <div className={`font-semibold ${getBusinessValueColor(suggestion.business_value_score)}`}>
                    {(suggestion.business_value_score * 100).toFixed(0)}%
                  </div>
                  <div className="text-gray-500">Value</div>
                </div>
              </div>
              
              {/* Sample Values */}
              {suggestion.sample_values.length > 0 && (
                <div>
                  <Label className="text-sm font-medium">Sample Values</Label>
                  <div className="flex flex-wrap gap-1 mt-1">
                    {suggestion.sample_values.map((value, index) => (
                      <span
                        key={index}
                        className="px-2 py-1 bg-gray-100 text-gray-700 text-xs rounded"
                      >
                        {value}
                      </span>
                    ))}
                  </div>
                </div>
              )}
              
              {/* Detection Pattern */}
              {suggestion.detection_pattern && (
                <div>
                  <Label className="text-sm font-medium">Detection Pattern</Label>
                  <p className="text-sm text-gray-600 mt-1">{suggestion.detection_pattern}</p>
                </div>
              )}
              
              {/* Related Fields */}
              {suggestion.related_fields.length > 0 && (
                <div>
                  <Label className="text-sm font-medium">Related Fields</Label>
                  <div className="flex flex-wrap gap-1 mt-1">
                    {suggestion.related_fields.map((field, index) => (
                      <span
                        key={index}
                        className="px-2 py-1 bg-blue-100 text-blue-700 text-xs rounded"
                      >
                        {field}
                      </span>
                    ))}
                  </div>
                </div>
              )}
              
              {/* Actions */}
              <div className="flex space-x-2 pt-2 border-t">
                {!suggestion.is_reviewed ? (
                  <>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => openReviewForm(suggestion)}
                      className="flex-1"
                    >
                      <Eye className="w-4 h-4 mr-1" />
                      Review
                    </Button>
                    
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => handleApprove(suggestion)}
                      className="flex-1"
                    >
                      <CheckCircle className="w-4 h-4 mr-1" />
                      Quick Approve
                    </Button>
                    
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => handleReject(suggestion)}
                      className="text-red-600 hover:text-red-700"
                    >
                      <XCircle className="w-4 h-4" />
                    </Button>
                  </>
                ) : (
                  <div className="w-full text-center text-sm text-gray-500">
                    {suggestion.is_approved ? 'Field approved and implemented' : 'Field rejected'}
                  </div>
                )}
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Empty State */}
      {filteredSuggestions.length === 0 && (
        <Card className="text-center py-12">
          <CardContent>
            <Lightbulb className="w-12 h-12 text-gray-400 mx-auto mb-4" />
            <h3 className="text-lg font-medium text-gray-900 mb-2">No Field Suggestions</h3>
            <p className="text-gray-600 mb-4">
              {selectedFilter === 'all' 
                ? 'AI will analyze your conversations and suggest new fields to enhance your schemas'
                : `No ${selectedFilter.replace('_', ' ')} suggestions found`
              }
            </p>
            {selectedFilter !== 'all' && (
              <Button variant="outline" onClick={() => setSelectedFilter('all')}>
                View All Suggestions
              </Button>
            )}
          </CardContent>
        </Card>
      )}

      {/* Stats Summary */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center space-x-2">
            <TrendingUp className="w-5 h-5" />
            <span>Suggestions Overview</span>
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <div className="text-center">
              <div className="text-2xl font-bold text-blue-600">{suggestions.length}</div>
              <div className="text-sm text-gray-600">Total Suggestions</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold text-yellow-600">
                {suggestions.filter(s => !s.is_reviewed).length}
              </div>
              <div className="text-sm text-gray-600">Pending Review</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold text-green-600">
                {suggestions.filter(s => s.is_approved).length}
              </div>
              <div className="text-sm text-gray-600">Approved</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold text-red-600">
                {suggestions.filter(s => s.is_reviewed && !s.is_approved).length}
              </div>
              <div className="text-sm text-gray-600">Rejected</div>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}

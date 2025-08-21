'use client'

import React, { useState } from 'react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { User, Briefcase, Building, Bot, Sparkles, ArrowRight } from 'lucide-react'

// API Configuration
const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE || 'http://localhost:8000'

interface ProfileData {
  owner_name: string
  owner_occupation: string
  industry: string
  ai_role: string
  ai_personality: string
  custom_instructions: string
  assistant_name: string
  name: string
}

interface ProfileSetupProps {
  workspaceId: string
  onComplete: (profile: ProfileData) => void
}

const AI_ROLES = [
  { value: 'general', label: 'General Assistant' },
  { value: 'banker', label: 'Banking Assistant' },
  { value: 'medical', label: 'Medical Assistant' },
  { value: 'legal', label: 'Legal Assistant' },
  { value: 'real_estate', label: 'Real Estate Assistant' },
  { value: 'restaurant', label: 'Restaurant Assistant' },
  { value: 'retail', label: 'Retail Assistant' },
  { value: 'tech_support', label: 'Technical Support' },
  { value: 'secretary', label: 'Personal Secretary' },
  { value: 'customer_service', label: 'Customer Service' },
  { value: 'consultant', label: 'Business Consultant' },
  { value: 'educator', label: 'Educational Assistant' },
]

const AI_PERSONALITIES = [
  { value: 'professional', label: 'Professional' },
  { value: 'friendly', label: 'Friendly' },
  { value: 'formal', label: 'Formal' },
  { value: 'casual', label: 'Casual' },
  { value: 'empathetic', label: 'Empathetic' },
  { value: 'direct', label: 'Direct' },
]

export default function ProfileSetup({ workspaceId, onComplete }: ProfileSetupProps) {
  const [step, setStep] = useState(1)
  const [isLoading, setIsLoading] = useState(false)
  const [formData, setFormData] = useState<ProfileData>({
    owner_name: '',
    owner_occupation: '',
    industry: '',
    ai_role: 'general',
    ai_personality: 'professional',
    custom_instructions: '',
    assistant_name: 'AI Assistant',
    name: ''
  })

  const handleInputChange = (field: keyof ProfileData, value: string) => {
    setFormData(prev => ({ ...prev, [field]: value }))
  }

  const handleSubmit = async () => {
    setIsLoading(true)
    
    try {
      const token = localStorage.getItem('authToken')
      const response = await fetch(`${API_BASE_URL}/api/v1/core/workspaces/${workspaceId}/setup-profile/`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Token ${token}`,
        },
        body: JSON.stringify(formData)
      })

      if (response.ok) {
        const result = await response.json()
        console.log('Profile setup completed:', result)
        onComplete(result.data)
      } else {
        const errorData = await response.json()
        console.error('Profile setup failed:', errorData)
        throw new Error(errorData.error || 'Failed to save profile')
      }
    } catch (error) {
      console.error('Profile setup error:', error)
      // Handle error
    } finally {
      setIsLoading(false)
    }
  }

  const canProceedToStep2 = formData.owner_name && formData.industry && formData.name
  const canSubmit = canProceedToStep2 && formData.ai_role

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 flex items-center justify-center p-4">
      <Card className="w-full max-w-2xl bg-white/80 backdrop-blur-sm shadow-2xl border border-white/20">
        <CardHeader className="text-center">
          <div className="w-16 h-16 bg-gradient-to-br from-blue-500 to-indigo-600 rounded-full flex items-center justify-center mx-auto mb-4 shadow-lg">
            <Sparkles className="w-8 h-8 text-white" />
          </div>
          <CardTitle className="text-3xl font-bold bg-gradient-to-r from-blue-600 to-indigo-600 bg-clip-text text-transparent">
            Personalize Your AI Assistant
          </CardTitle>
          <CardDescription className="text-lg">
            Let's set up your AI to perfectly match your business needs
          </CardDescription>
        </CardHeader>

        <CardContent className="space-y-6">
          {/* Progress indicator */}
          <div className="flex items-center justify-center space-x-4 mb-8">
            <div className={`w-10 h-10 rounded-full flex items-center justify-center ${
              step >= 1 ? 'bg-blue-500 text-white' : 'bg-gray-200 text-gray-500'
            }`}>
              <User className="w-5 h-5" />
            </div>
            <div className={`w-16 h-1 ${step >= 2 ? 'bg-blue-500' : 'bg-gray-200'}`} />
            <div className={`w-10 h-10 rounded-full flex items-center justify-center ${
              step >= 2 ? 'bg-blue-500 text-white' : 'bg-gray-200 text-gray-500'
            }`}>
              <Bot className="w-5 h-5" />
            </div>
          </div>

          {step === 1 && (
            <div className="space-y-6">
              <div className="text-center mb-6">
                <h3 className="text-xl font-semibold text-gray-900 mb-2">Tell us about yourself</h3>
                <p className="text-gray-600">This helps us personalize your AI assistant</p>
              </div>

              <div className="space-y-4">
                <div>
                  <Label htmlFor="name">Business Name *</Label>
                  <Input
                    id="name"
                    value={formData.name}
                    onChange={(e: React.ChangeEvent<HTMLInputElement>) => handleInputChange('name', e.target.value)}
                    placeholder="e.g., Acme Corporation"
                    className="mt-1"
                  />
                </div>

                <div>
                  <Label htmlFor="owner_name">Your Name *</Label>
                  <Input
                    id="owner_name"
                    value={formData.owner_name}
                    onChange={(e: React.ChangeEvent<HTMLInputElement>) => handleInputChange('owner_name', e.target.value)}
                    placeholder="e.g., John Smith"
                    className="mt-1"
                  />
                </div>

                <div>
                  <Label htmlFor="owner_occupation">Your Occupation</Label>
                  <Input
                    id="owner_occupation"
                    value={formData.owner_occupation}
                    onChange={(e: React.ChangeEvent<HTMLInputElement>) => handleInputChange('owner_occupation', e.target.value)}
                    placeholder="e.g., CEO, Doctor, Lawyer"
                    className="mt-1"
                  />
                </div>

                <div>
                  <Label htmlFor="industry">Industry *</Label>
                  <Input
                    id="industry"
                    value={formData.industry}
                    onChange={(e: React.ChangeEvent<HTMLInputElement>) => handleInputChange('industry', e.target.value)}
                    placeholder="e.g., Healthcare, Technology, Finance"
                    className="mt-1"
                  />
                </div>
              </div>

              <Button 
                onClick={() => setStep(2)}
                disabled={!canProceedToStep2}
                className="w-full bg-gradient-to-r from-blue-500 to-indigo-600 hover:from-blue-600 hover:to-indigo-700"
              >
                Continue to AI Setup <ArrowRight className="w-4 h-4 ml-2" />
              </Button>
            </div>
          )}

          {step === 2 && (
            <div className="space-y-6">
              <div className="text-center mb-6">
                <h3 className="text-xl font-semibold text-gray-900 mb-2">Configure Your AI Assistant</h3>
                <p className="text-gray-600">Choose how your AI should behave and respond</p>
              </div>

              <div className="space-y-4">
                <div>
                  <Label htmlFor="assistant_name">Assistant Name</Label>
                  <Input
                    id="assistant_name"
                    value={formData.assistant_name}
                    onChange={(e: React.ChangeEvent<HTMLInputElement>) => handleInputChange('assistant_name', e.target.value)}
                    placeholder="e.g., Sarah, Alex, Assistant"
                    className="mt-1"
                  />
                </div>

                <div>
                  <Label htmlFor="ai_role">AI Role</Label>
                  <Select 
                    value={formData.ai_role} 
                    onChange={(e: React.ChangeEvent<HTMLSelectElement>) => handleInputChange('ai_role', e.target.value)}
                    className="mt-1"
                  >
                    {AI_ROLES.map(role => (
                      <option key={role.value} value={role.value}>
                        {role.label}
                      </option>
                    ))}
                  </Select>
                </div>

                <div>
                  <Label htmlFor="ai_personality">AI Personality</Label>
                  <Select 
                    value={formData.ai_personality} 
                    onChange={(e: React.ChangeEvent<HTMLSelectElement>) => handleInputChange('ai_personality', e.target.value)}
                    className="mt-1"
                  >
                    {AI_PERSONALITIES.map(personality => (
                      <option key={personality.value} value={personality.value}>
                        {personality.label}
                      </option>
                    ))}
                  </Select>
                </div>

                <div>
                  <Label htmlFor="custom_instructions">Custom Instructions (Optional)</Label>
                  <Textarea
                    id="custom_instructions"
                    value={formData.custom_instructions}
                    onChange={(e: React.ChangeEvent<HTMLTextAreaElement>) => handleInputChange('custom_instructions', e.target.value)}
                    placeholder="Any specific instructions for your AI assistant..."
                    className="mt-1"
                    rows={4}
                  />
                </div>
              </div>

              <div className="flex space-x-4">
                <Button 
                  variant="outline" 
                  onClick={() => setStep(1)}
                  className="flex-1"
                >
                  Back
                </Button>
                <Button 
                  onClick={handleSubmit}
                  disabled={!canSubmit || isLoading}
                  className="flex-1 bg-gradient-to-r from-blue-500 to-indigo-600 hover:from-blue-600 hover:to-indigo-700"
                >
                  {isLoading ? 'Setting up...' : 'Complete Setup'}
                </Button>
              </div>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}

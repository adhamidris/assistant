'use client'

import { useSearchParams, useRouter } from 'next/navigation'
import { Suspense } from 'react'
import ProfileSetup from '@/components/ProfileSetup'

function ProfileSetupContent() {
  const searchParams = useSearchParams()
  const router = useRouter()
  const workspaceId = searchParams.get('workspace') || 'fd41c725-4d89-4af3-af89-55d2dd97f33d'

  const handleProfileComplete = (profile: any) => {
    console.log('Profile setup completed:', profile)
    
    // Check if authentication data is still available
    const token = localStorage.getItem('authToken')
    const userData = localStorage.getItem('userData')
    const workspaceId = localStorage.getItem('workspaceId')
    
    console.log('Auth data check after profile completion:', {
      token: token ? 'Found' : 'Missing',
      userData: userData ? 'Found' : 'Missing',
      workspaceId: workspaceId ? 'Found' : 'Missing'
    })
    
    // Redirect to dashboard using router
    console.log('Redirecting to dashboard...')
    router.push('/dashboard')
  }

  return (
    <ProfileSetup 
      workspaceId={workspaceId}
      onComplete={handleProfileComplete}
    />
  )
}

export default function ProfileSetupPage() {
  return (
    <Suspense fallback={<div>Loading...</div>}>
      <ProfileSetupContent />
    </Suspense>
  )
}

'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { 
  MessageSquare, 
  Users, 
  FileText, 
  Settings, 
  BarChart3,
  Bot,
  Clock,
  CheckCircle,
  AlertCircle,
  TrendingUp,
  Calendar,
  Share2
} from 'lucide-react'
import { getConversations, getContacts, getDrafts } from '@/lib/api'
import ConversationList from '@/components/ConversationList'
import ContactList from '@/components/ContactList'
import DraftManagement from '@/components/DraftManagement'
import AppointmentsList from '@/components/AppointmentsList'
import KnowledgeBaseManager from '@/components/KnowledgeBaseManager'
import PortalLinkGenerator from '@/components/PortalLinkGenerator'
import NotificationBell from '@/components/NotificationBell'

// API Configuration
const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE || 'http://localhost:8000'

type TabType = 'conversations' | 'contacts' | 'drafts' | 'appointments' | 'knowledge' | 'analytics' | 'portal'

export default function Dashboard() {
  const [activeTab, setActiveTab] = useState<TabType>('conversations')
  const [stats, setStats] = useState({
    totalConversations: 0,
    activeConversations: 0,
    totalContacts: 0,
    pendingDrafts: 0,
    responseTime: '2.3s',
    satisfactionRate: '94%'
  })
  const [appointments, setAppointments] = useState([])
  const [isLoading, setIsLoading] = useState(true)

  // Get workspace ID from authentication
  const [workspaceId, setWorkspaceId] = useState<string | null>(null)
  const [userData, setUserData] = useState<any>(null)
  const router = useRouter()

  useEffect(() => {
    // Wait for the browser to be ready
    const checkAuth = () => {
      // Check authentication
      const token = localStorage.getItem('authToken')
      const storedUserData = localStorage.getItem('userData')
      const storedWorkspaceId = localStorage.getItem('workspaceId')
      
      console.log('Dashboard auth check:', {
        token: token ? 'Found' : 'Missing',
        userData: storedUserData ? 'Found' : 'Missing',
        workspaceId: storedWorkspaceId ? 'Found' : 'Missing',
        tokenValue: token ? `${token.substring(0, 10)}...` : 'None',
        workspaceIdValue: storedWorkspaceId || 'None',
        userDataValue: storedUserData ? JSON.parse(storedUserData) : 'None'
      })
      
      // Only redirect if ALL authentication data is missing
      if (!token && !storedUserData && !storedWorkspaceId) {
        console.log('All auth data missing, redirecting to login')
        try {
          router.push('/login')
        } catch (error) {
          console.error('Router redirect failed, using window.location:', error)
          window.location.href = '/login'
        }
        return
      }
      
      // If we have some but not all data, try to recover
      if (!token || !storedUserData || !storedWorkspaceId) {
        console.log('Partial auth data missing, attempting to recover...')
        // Don't redirect immediately, let the API calls handle it
      }
      
      try {
        if (storedUserData) {
          setUserData(JSON.parse(storedUserData))
        }
        if (storedWorkspaceId) {
          setWorkspaceId(storedWorkspaceId)
        }
        console.log('Auth data loaded successfully')
      } catch (error) {
        console.error('Error parsing user data:', error)
        // Don't redirect immediately, let the API calls handle it
      }
    }
    
    // Check immediately
    checkAuth()
    
    // Also check after a short delay to ensure localStorage is ready
    const timeoutId = setTimeout(checkAuth, 100)
    
    return () => clearTimeout(timeoutId)
  }, [router])

  // Separate useEffect to handle profile check after workspaceId is set
  useEffect(() => {
    if (workspaceId) {
      checkProfileSetup()
    }
  }, [workspaceId])

  // Add timeout fallback to prevent infinite loading
  useEffect(() => {
    const timeout = setTimeout(() => {
      if (isLoading) {
        console.log('Dashboard loading timeout - forcing load completion')
        setIsLoading(false)
      }
    }, 10000) // 10 second timeout

    return () => clearTimeout(timeout)
  }, [isLoading])
  
  const checkProfileSetup = async () => {
    if (!workspaceId) return
    
    try {
      console.log('Checking profile setup for workspace:', workspaceId)
      const token = localStorage.getItem('authToken')
      
      // Check if we have a token before making the API call
      if (!token) {
        console.log('No token available for profile check, skipping...')
        loadDashboardData()
        return
      }
      
      const response = await fetch(`${API_BASE_URL}/api/v1/core/workspaces/${workspaceId}/profile-status/`, {
        headers: {
          'Authorization': `Token ${token}`,
          'Content-Type': 'application/json',
        }
      })
      
      if (!response.ok) {
        console.log('Profile status check failed, continuing to dashboard anyway...')
        loadDashboardData()
        return
      }
      
      const data = await response.json()
      console.log('Profile status response:', data)
      
      if (!data.profile_completed) {
        // Redirect to profile setup using router
        console.log('Profile not completed, redirecting to profile setup...')
        try {
          router.push(`/profile-setup?workspace=${workspaceId}`)
        } catch (error) {
          console.error('Router redirect failed, using window.location:', error)
          window.location.href = `/profile-setup?workspace=${workspaceId}`
        }
        return
      }
      
      // Profile is complete, load dashboard
      loadDashboardData()
    } catch (error) {
      console.error('Error checking profile:', error)
      // Continue to dashboard even if profile check fails
      console.log('Profile check failed, loading dashboard anyway...')
      loadDashboardData()
    }
  }

  const loadDashboardData = async () => {
    if (!workspaceId) return
    
    try {
      setIsLoading(true)
      console.log('Loading dashboard data for workspace:', workspaceId)
      
      // Check if user is still authenticated before making API calls
      const currentToken = localStorage.getItem('authToken')
      if (!currentToken) {
        console.log('Token missing during data load, redirecting to login')
        router.push('/login')
        return
      }
      
      // Load dashboard statistics and appointments
      const [conversations, contacts, drafts, appointmentResponse] = await Promise.all([
        getConversations(workspaceId).catch(error => {
          console.error('Failed to load conversations:', error)
          return []
        }),
        getContacts(workspaceId).catch(error => {
          console.error('Failed to load contacts:', error)
          return []
        }),
        getDrafts().catch(error => {
          console.error('Failed to load drafts:', error)
          return []
        }),
        fetch(`${API_BASE_URL}/api/v1/calendar/appointments/?workspace=${workspaceId}`).catch(() => ({ ok: false }))
      ])
      
      console.log('Loaded data:', { conversations, contacts, drafts })
      
      // Load appointments if API is available
      let appointmentData = []
      if (appointmentResponse.ok && 'json' in appointmentResponse) {
        try {
          const appointmentResult = await appointmentResponse.json()
          appointmentData = appointmentResult.results || appointmentResult || []
        } catch (error) {
          console.error('Failed to parse appointment data:', error)
        }
      }

      // Ensure we have arrays for the data
      const conversationsArray = Array.isArray(conversations) ? conversations : (conversations?.results || [])
      const contactsArray = Array.isArray(contacts) ? contacts : (contacts?.results || [])
      const draftsArray = Array.isArray(drafts) ? drafts : (drafts?.results || [])

      setAppointments(appointmentData)
      setStats({
        totalConversations: conversationsArray.length || 0,
        activeConversations: conversationsArray.filter((c: any) => c.status === 'active').length || 0,
        totalContacts: contactsArray.length || 0,
        pendingDrafts: draftsArray.length || 0,
        responseTime: '2.3s',
        satisfactionRate: '94%'
      })
      
      console.log('Dashboard data loaded successfully')
    } catch (error) {
      console.error('Failed to load dashboard data:', error)
      // Set default stats even if loading fails
      setStats({
        totalConversations: 0,
        activeConversations: 0,
        totalContacts: 0,
        pendingDrafts: 0,
        responseTime: '2.3s',
        satisfactionRate: '94%'
      })
      setAppointments([])
    } finally {
      setIsLoading(false)
    }
  }

  const tabs = [
    { id: 'conversations', label: 'Conversations', icon: MessageSquare, badge: undefined },
    { id: 'contacts', label: 'Contacts', icon: Users, badge: undefined },
    { id: 'drafts', label: 'Drafts', icon: Clock, badge: stats.pendingDrafts },
    { id: 'appointments', label: 'Appointments', icon: Calendar, badge: appointments.length },
    { id: 'knowledge', label: 'Knowledge Base', icon: FileText, badge: undefined },
    { id: 'analytics', label: 'Analytics', icon: BarChart3, badge: undefined },
    { id: 'portal', label: 'Portal Link', icon: Share2, badge: undefined }
  ] as const

  if (isLoading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="w-8 h-8 border-2 border-blue-600 border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
          <p className="text-gray-600">Loading dashboard...</p>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white shadow-sm border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center py-4">
            <div className="flex items-center space-x-3">
              <Bot className="h-8 w-8 text-blue-600" />
              <div>
                <h1 className="text-2xl font-bold text-gray-900">Business Dashboard</h1>
                <p className="text-sm text-gray-500">AI Personal Business Assistant</p>
              </div>
            </div>
            <div className="flex items-center space-x-4">
              <NotificationBell />
              <button className="p-2 text-gray-400 hover:text-gray-600">
                <Settings className="w-5 h-5" />
              </button>
            </div>
          </div>
        </div>
      </header>

      {/* Stats Cards */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
          <StatsCard
            title="Total Conversations"
            value={stats.totalConversations}
            icon={MessageSquare}
            color="blue"
            change="+12%"
          />
          <StatsCard
            title="Active Contacts"
            value={stats.totalContacts}
            icon={Users}
            color="green"
            change="+5%"
          />
          <StatsCard
            title="Pending Drafts"
            value={stats.pendingDrafts}
            icon={Clock}
            color="yellow"
            change={stats.pendingDrafts > 0 ? 'Action needed' : 'All clear'}
          />
          <StatsCard
            title="Avg Response Time"
            value={stats.responseTime}
            icon={TrendingUp}
            color="purple"
            change="-0.5s"
          />
        </div>

        {/* Navigation Tabs */}
        <div className="bg-white rounded-lg shadow-sm mb-6">
          <div className="border-b border-gray-200">
            <nav className="-mb-px flex space-x-8 px-6">
              {tabs.map((tab) => {
                const Icon = tab.icon
                return (
                  <button
                    key={tab.id}
                    onClick={() => setActiveTab(tab.id)}
                    className={`py-4 px-1 border-b-2 font-medium text-sm flex items-center space-x-2 ${
                      activeTab === tab.id
                        ? 'border-blue-500 text-blue-600'
                        : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                    }`}
                  >
                    <Icon className="w-4 h-4" />
                    <span>{tab.label}</span>
                    {tab.badge && tab.badge > 0 && (
                      <span className="bg-red-100 text-red-800 text-xs font-medium px-2 py-1 rounded-full">
                        {tab.badge}
                      </span>
                    )}
                  </button>
                )
              })}
            </nav>
          </div>

          {/* Tab Content */}
          <div className="p-6">
            {activeTab === 'conversations' && workspaceId && <ConversationList workspaceId={workspaceId} />}
            {activeTab === 'contacts' && workspaceId && <ContactList workspaceId={workspaceId} />}
            {activeTab === 'drafts' && <DraftManagement />}
            {activeTab === 'appointments' && <AppointmentsList appointments={appointments} />}
            {activeTab === 'knowledge' && workspaceId && <KnowledgeBaseManager workspaceId={workspaceId} />}
            {activeTab === 'analytics' && <AnalyticsDashboard />}
            {activeTab === 'portal' && workspaceId && <PortalLinkGenerator workspaceId={workspaceId} />}
          </div>
        </div>
      </div>
    </div>
  )
}

function StatsCard({ 
  title, 
  value, 
  icon: Icon, 
  color, 
  change 
}: { 
  title: string
  value: string | number
  icon: any
  color: string
  change: string 
}) {
  const colorClasses = {
    blue: 'bg-blue-100 text-blue-600',
    green: 'bg-green-100 text-green-600',
    yellow: 'bg-yellow-100 text-yellow-600',
    purple: 'bg-purple-100 text-purple-600'
  }

  return (
    <div className="bg-white rounded-lg shadow-sm p-6">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-sm font-medium text-gray-600">{title}</p>
          <p className="text-2xl font-bold text-gray-900">{value}</p>
        </div>
        <div className={`w-12 h-12 rounded-lg flex items-center justify-center ${colorClasses[color as keyof typeof colorClasses]}`}>
          <Icon className="w-6 h-6" />
        </div>
      </div>
      <div className="mt-4">
        <span className={`text-sm ${
          change.includes('+') || change.includes('-') 
            ? change.includes('+') ? 'text-green-600' : 'text-red-600'
            : 'text-gray-600'
        }`}>
          {change}
        </span>
      </div>
    </div>
  )
}

function AnalyticsDashboard() {
  return (
    <div className="space-y-6">
      <h3 className="text-lg font-semibold text-gray-900">Analytics & Insights</h3>
      
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-gray-50 rounded-lg p-6">
          <h4 className="text-md font-medium text-gray-900 mb-4">Response Performance</h4>
          <div className="space-y-3">
            <div className="flex justify-between">
              <span className="text-sm text-gray-600">Average Response Time</span>
              <span className="text-sm font-medium">2.3s</span>
            </div>
            <div className="flex justify-between">
              <span className="text-sm text-gray-600">AI Success Rate</span>
              <span className="text-sm font-medium">87%</span>
            </div>
            <div className="flex justify-between">
              <span className="text-sm text-gray-600">Customer Satisfaction</span>
              <span className="text-sm font-medium">94%</span>
            </div>
          </div>
        </div>

        <div className="bg-gray-50 rounded-lg p-6">
          <h4 className="text-md font-medium text-gray-900 mb-4">Message Types</h4>
          <div className="space-y-3">
            <div className="flex justify-between">
              <span className="text-sm text-gray-600">Text Messages</span>
              <span className="text-sm font-medium">76%</span>
            </div>
            <div className="flex justify-between">
              <span className="text-sm text-gray-600">Audio Messages</span>
              <span className="text-sm font-medium">18%</span>
            </div>
            <div className="flex justify-between">
              <span className="text-sm text-gray-600">File Uploads</span>
              <span className="text-sm font-medium">6%</span>
            </div>
          </div>
        </div>
      </div>

      <div className="text-center py-12">
        <BarChart3 className="w-12 h-12 text-gray-400 mx-auto mb-4" />
        <p className="text-gray-500">Detailed analytics coming soon...</p>
      </div>
    </div>
  )
}


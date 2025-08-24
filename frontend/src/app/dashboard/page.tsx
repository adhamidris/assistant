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
  Calendar,
  Share2,
  LayoutDashboard,
  Database,
  Workflow,
  Lightbulb,
  Shield,
  Zap,
  TrendingUp,
  Building2,
  Sparkles,
  Activity,
  CheckCircle
} from 'lucide-react'
import { getConversations, getContacts, getDrafts } from '@/lib/api'
import ConversationList from '@/components/ConversationList'
import ContactList from '@/components/ContactList'
import DraftManagement from '@/components/DraftManagement'
import AppointmentsList from '@/components/AppointmentsList'
import KnowledgeBaseManager from '@/components/KnowledgeBaseManager'
import PortalLinkGenerator from '@/components/PortalLinkGenerator'
import NotificationBell from '@/components/NotificationBell'
import ContextSchemasManager from '@/components/ContextSchemasManager'
import BusinessRulesManager from '@/components/BusinessRulesManager'
import AgentManager from '@/components/AgentManager'
import BusinessTypeSetup from '@/components/BusinessTypeSetup'
import FieldSuggestionsManager from '@/components/FieldSuggestionsManager'
import { CaseManager } from '@/components/CaseManager'
import TestingDashboard from '@/components/TestingDashboard'
import DashboardCard from '@/components/ui/dashboard-card'
import Sidebar from '@/components/ui/sidebar'
import NavItem from '@/components/ui/nav-item'
import StatsCard from '@/components/ui/stats-card'

// API Configuration
const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE || 'http://localhost:8000'

type TabType = 'overview' | 'conversations' | 'contacts' | 'drafts' | 'appointments' | 'knowledge' | 'context-schemas' | 'business-rules' | 'ai-agents' | 'business-setup' | 'field-suggestions' | 'cases' | 'testing' | 'analytics' | 'portal'

interface NavigationItem {
  id: TabType
  label: string
  icon: any
  badge: number | undefined
}

interface NavigationSection {
  title: string
  items: NavigationItem[]
}

export default function Dashboard() {
  const [activeTab, setActiveTab] = useState<TabType>('overview')
  const router = useRouter()
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false)
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

  useEffect(() => {
    // Check for tab query parameter
    const urlParams = new URLSearchParams(window.location.search)
    const tabParam = urlParams.get('tab') as TabType
    if (tabParam && ['overview', 'conversations', 'contacts', 'drafts', 'appointments', 'knowledge', 'context-schemas', 'business-rules', 'ai-agents', 'business-setup', 'field-suggestions', 'cases', 'testing', 'analytics', 'portal'].includes(tabParam)) {
      setActiveTab(tabParam)
    }

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

    // Wait for browser to be ready
    if (typeof window !== 'undefined') {
      checkAuth()
    }
  }, [router])

  useEffect(() => {
    if (!workspaceId) return

    const loadDashboardData = async () => {
      try {
        console.log('Loading dashboard data for workspace:', workspaceId)
        
        // Load all data in parallel
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

    loadDashboardData()
  }, [workspaceId])

  // Navigation structure with organized sections
  const navigationSections: NavigationSection[] = [
    {
      title: 'Overview',
      items: [
        { id: 'overview', label: 'Dashboard', icon: LayoutDashboard, badge: undefined }
      ]
    },
    {
      title: 'Communication',
      items: [
        { id: 'conversations', label: 'Conversations', icon: MessageSquare, badge: stats.activeConversations },
        { id: 'contacts', label: 'Contacts', icon: Users, badge: stats.totalContacts },
        { id: 'drafts', label: 'Drafts', icon: Clock, badge: stats.pendingDrafts },
        { id: 'appointments', label: 'Appointments', icon: Calendar, badge: appointments.length }
      ]
    },
    {
      title: 'AI & Intelligence',
      items: [
        { id: 'ai-agents', label: 'AI Agents', icon: Bot, badge: undefined },
        { id: 'knowledge', label: 'Knowledge Base', icon: FileText, badge: undefined },
        { id: 'field-suggestions', label: 'Field Suggestions', icon: Lightbulb, badge: undefined }
      ]
    },
    {
      title: 'Business Logic',
      items: [
        { id: 'context-schemas', label: 'Context Schemas', icon: Database, badge: undefined },
        { id: 'business-rules', label: 'Business Rules', icon: Workflow, badge: undefined },
        { id: 'business-setup', label: 'Business Setup', icon: Building2, badge: undefined },
        { id: 'cases', label: 'Case Management', icon: FileText, badge: undefined }
      ]
    },
    {
      title: 'Testing & Analytics',
      items: [
        { id: 'testing', label: 'Testing Dashboard', icon: Shield, badge: undefined },
        { id: 'analytics', label: 'Analytics', icon: TrendingUp, badge: undefined }
      ]
    },
    {
      title: 'System',
      items: [
        { id: 'portal', label: 'Portal Link', icon: Share2, badge: undefined }
      ]
    }
  ]

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
    <div className="min-h-screen bg-gray-50 flex">
      {/* Left Sidebar */}
      <Sidebar
        collapsed={sidebarCollapsed}
        onToggle={() => setSidebarCollapsed(!sidebarCollapsed)}
      >
        {/* Sidebar Header */}
        <div className="p-4 border-b border-gray-200">
          <div className="flex items-center space-x-3">
            <div className="w-8 h-8 bg-gradient-to-br from-blue-500 to-purple-600 rounded-lg flex items-center justify-center">
              <Bot className="w-5 h-5 text-white" />
            </div>
            {!sidebarCollapsed && (
              <div>
                <h1 className="text-lg font-bold text-gray-900">AI Assistant</h1>
                <p className="text-xs text-gray-500">Business Dashboard</p>
              </div>
            )}
          </div>
        </div>

        {/* Navigation Sections */}
        <nav className="p-4 space-y-6">
          {navigationSections.map((section, sectionIndex) => (
            <div key={sectionIndex}>
              {!sidebarCollapsed && (
                <h3 className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-3 px-2">
                  {section.title}
                </h3>
              )}
              <div className="space-y-1">
                {section.items.map((item) => {
                  const Icon = item.icon
                  const isActive = activeTab === item.id
                  return (
                    <NavItem
                      key={item.id}
                      icon={Icon}
                      label={item.label}
                      badge={item.badge}
                      active={isActive}
                      collapsed={sidebarCollapsed}
                      onClick={() => setActiveTab(item.id as TabType)}
                    />
                  )
                })}
              </div>
            </div>
          ))}
        </nav>

        {/* User Profile Section */}
        {!sidebarCollapsed && (
          <div className="absolute bottom-0 left-0 right-0 p-4 border-t border-gray-200 bg-white">
            <div className="flex items-center space-x-3">
              <div className="w-8 h-8 bg-gradient-to-br from-green-400 to-blue-500 rounded-full flex items-center justify-center">
                <span className="text-sm font-semibold text-white">
                  {userData?.first_name?.[0] || userData?.username?.[0] || 'U'}
                </span>
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium text-gray-900 truncate">
                  {userData?.first_name && userData?.last_name
                    ? `${userData.first_name} ${userData.last_name}`
                    : userData?.username || 'User'
                  }
                </p>
                <p className="text-xs text-gray-500 truncate">
                  {userData?.email || 'user@example.com'}
                </p>
              </div>
            </div>
          </div>
        )}
      </Sidebar>

      {/* Main Content Area */}
      <div className="flex-1 flex flex-col">
        {/* Top Header */}
        <header className="bg-white shadow-sm border-b border-gray-200 px-6 py-4">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-2xl font-bold text-gray-900">
                {navigationSections
                  .flatMap(section => section.items)
                  .find(item => item.id === activeTab)?.label || 'Dashboard'
                }
              </h2>
              <p className="text-sm text-gray-600 mt-1">
                {activeTab === 'overview' 
                  ? 'Welcome to your AI-powered business dashboard'
                  : `Manage your ${navigationSections
                      .flatMap(section => section.items)
                      .find(item => item.id === activeTab)?.label.toLowerCase() || 'dashboard'
                    }`
                }
              </p>
            </div>
            <div className="flex items-center space-x-4">
              <NotificationBell />
              <div className="w-px h-6 bg-gray-300"></div>
              <div className="text-right">
                <p className="text-sm font-medium text-gray-900">
                  {userData?.workspace?.name || 'Business'}
                </p>
                <p className="text-xs text-gray-500">Active Workspace</p>
              </div>
            </div>
          </div>
        </header>

        {/* Main Content */}
        <main className="flex-1 p-6 overflow-auto">
          {activeTab === 'overview' && (
            <div className="space-y-6">
              {/* Welcome Section */}
              <div className="bg-gradient-to-r from-blue-600 to-purple-600 rounded-xl p-6 text-white">
                <div className="flex items-center space-x-4">
                  <div className="w-12 h-12 bg-white/20 rounded-lg flex items-center justify-center">
                    <Sparkles className="w-6 h-6" />
                  </div>
                  <div>
                    <h3 className="text-xl font-bold">Welcome back!</h3>
                    <p className="text-blue-100">
                      Your AI-powered business assistant is ready to help you grow.
                    </p>
                  </div>
                </div>
              </div>

              {/* Stats Grid */}
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
                <StatsCard
                  title="Active Conversations"
                  value={stats.activeConversations}
                  icon={MessageSquare}
                  color="blue"
                  change={`${stats.totalConversations} total`}
                  trend="up"
                />
                <StatsCard
                  title="Total Contacts"
                  value={stats.totalContacts}
                  icon={Users}
                  color="green"
                  change="Growing network"
                  trend="up"
                />
                <StatsCard
                  title="Pending Drafts"
                  value={stats.pendingDrafts}
                  icon={Clock}
                  color="yellow"
                  change="Needs attention"
                  trend={stats.pendingDrafts > 0 ? "down" : "neutral"}
                />
                <StatsCard
                  title="Response Time"
                  value={stats.responseTime}
                  icon={Zap}
                  color="purple"
                  change="Fast & efficient"
                  trend="up"
                />
              </div>

              {/* Quick Actions */}
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                <DashboardCard>
                  <h3 className="text-lg font-semibold text-gray-900 mb-4 flex items-center">
                    <Zap className="w-5 h-5 text-blue-600 mr-2" />
                    Quick Actions
                  </h3>
                  <div className="space-y-3">
                    <button
                      onClick={() => setActiveTab('conversations')}
                      className="w-full flex items-center space-x-3 p-3 rounded-lg border border-gray-200 hover:border-blue-300 hover:bg-blue-50 transition-colors"
                    >
                      <MessageSquare className="w-5 h-5 text-blue-600" />
                      <span className="text-sm font-medium text-gray-700">Start New Conversation</span>
                    </button>
                    <button
                      onClick={() => setActiveTab('ai-agents')}
                      className="w-full flex items-center space-x-3 p-3 rounded-lg border border-gray-200 hover:border-green-300 hover:bg-green-50 transition-colors"
                    >
                      <Bot className="w-5 h-5 text-green-600" />
                      <span className="text-sm font-medium text-gray-700">Configure AI Agents</span>
                    </button>
                    <button
                      onClick={() => setActiveTab('business-rules')}
                      className="w-full flex items-center space-x-3 p-3 rounded-lg border border-gray-200 hover:border-purple-300 hover:bg-purple-50 transition-colors"
                    >
                      <Workflow className="w-5 h-5 text-purple-600" />
                      <span className="text-sm font-medium text-gray-700">Set Business Rules</span>
                    </button>
                  </div>
                </DashboardCard>

                <DashboardCard>
                  <h3 className="text-lg font-semibold text-gray-900 mb-4 flex items-center">
                    <Activity className="w-5 h-5 text-green-600 mr-2" />
                    System Status
                  </h3>
                  <div className="space-y-3">
                    <div className="flex items-center justify-between">
                      <span className="text-sm text-gray-600">AI Services</span>
                      <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800">
                        <CheckCircle className="w-3 h-3 mr-1" />
                        Operational
                      </span>
                    </div>
                    <div className="flex items-center justify-between">
                      <span className="text-sm text-gray-600">Database</span>
                      <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800">
                        <CheckCircle className="w-3 h-3 mr-1" />
                        Healthy
                      </span>
                    </div>
                    <div className="flex items-center justify-between">
                      <span className="text-sm text-gray-600">Background Tasks</span>
                      <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800">
                        <CheckCircle className="w-3 h-3 mr-1" />
                        Active
                      </span>
                    </div>
                  </div>
                </DashboardCard>
              </div>
            </div>
          )}

          {activeTab === 'conversations' && workspaceId && <ConversationList workspaceId={workspaceId} />}
          {activeTab === 'contacts' && workspaceId && <ContactList workspaceId={workspaceId} />}
          {activeTab === 'drafts' && <DraftManagement />}
          {activeTab === 'appointments' && <AppointmentsList appointments={appointments} />}
          {activeTab === 'knowledge' && workspaceId && <KnowledgeBaseManager workspaceId={workspaceId} />}
          {activeTab === 'context-schemas' && workspaceId && <ContextSchemasManager workspaceId={workspaceId} />}
          {activeTab === 'business-rules' && workspaceId && <BusinessRulesManager workspaceId={workspaceId} />}
          {activeTab === 'ai-agents' && workspaceId && <AgentManager workspaceId={workspaceId} />}
          {activeTab === 'business-setup' && workspaceId && <BusinessTypeSetup workspaceId={workspaceId} />}
          {activeTab === 'field-suggestions' && workspaceId && <FieldSuggestionsManager workspaceId={workspaceId} />}
          {activeTab === 'cases' && workspaceId && <CaseManager workspaceId={workspaceId} />}
          {activeTab === 'testing' && <TestingDashboard />}
          {activeTab === 'analytics' && <AnalyticsDashboard />}
          {activeTab === 'portal' && workspaceId && <PortalLinkGenerator workspaceId={workspaceId} />}
        </main>
      </div>
    </div>
  )
}



function AnalyticsDashboard() {
  return (
    <div className="space-y-6">
      <DashboardCard>
        <h3 className="text-lg font-semibold text-gray-900 mb-4 flex items-center">
          <BarChart3 className="w-5 h-5 text-blue-600 mr-2" />
          Analytics & Insights
        </h3>
        
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
      </DashboardCard>
    </div>
  )
}


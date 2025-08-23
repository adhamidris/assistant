'use client'

import React, { useState, useEffect } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { 
  Play, 
  CheckCircle, 
  XCircle, 
  AlertTriangle, 
  Clock, 
  Zap,
  Users,
  Bot,
  Settings,
  BarChart3,
  Database,
  Workflow
} from 'lucide-react'

interface TestResult {
  id: string
  name: string
  status: 'pending' | 'running' | 'passed' | 'failed' | 'skipped'
  duration?: number
  error?: string
  details?: string
  timestamp: string
}

interface TestSuite {
  id: string
  name: string
  description: string
  tests: TestResult[]
  status: 'pending' | 'running' | 'completed'
  totalTests: number
  passedTests: number
  failedTests: number
  skippedTests: number
}

interface SystemHealth {
  database: 'healthy' | 'warning' | 'critical'
  api: 'healthy' | 'warning' | 'critical'
  ai_services: 'healthy' | 'warning' | 'critical'
  background_tasks: 'healthy' | 'warning' | 'critical'
}

const TestingDashboard: React.FC = () => {
  const [testSuites, setTestSuites] = useState<TestSuite[]>([])
  const [systemHealth, setSystemHealth] = useState<SystemHealth>({
    database: 'healthy',
    api: 'healthy',
    ai_services: 'healthy',
    background_tasks: 'healthy'
  })
  const [isRunningTests, setIsRunningTests] = useState(false)
  const [activeTestSuite, setActiveTestSuite] = useState<string | null>(null)

  useEffect(() => {
    initializeTestSuites()
    checkSystemHealth()
  }, [])

  const initializeTestSuites = () => {
    const suites: TestSuite[] = [
      {
        id: 'system-integration',
        name: 'System Integration Tests',
        description: 'Tests all components working together',
        tests: [
          { id: '1', name: 'Database Connectivity', status: 'pending', timestamp: new Date().toISOString() },
          { id: '2', name: 'API Endpoints', status: 'pending', timestamp: new Date().toISOString() },
          { id: '3', name: 'Context Schema System', status: 'pending', timestamp: new Date().toISOString() },
          { id: '4', name: 'Business Rules Engine', status: 'pending', timestamp: new Date().toISOString() },
          { id: '5', name: 'Field Discovery System', status: 'pending', timestamp: new Date().toISOString() },
          { id: '6', name: 'Multi-Agent System', status: 'pending', timestamp: new Date().toISOString() },
          { id: '7', name: 'Data Flow Integration', status: 'pending', timestamp: new Date().toISOString() },
          { id: '8', name: 'Backward Compatibility', status: 'pending', timestamp: new Date().toISOString() }
        ],
        status: 'pending',
        totalTests: 8,
        passedTests: 0,
        failedTests: 0,
        skippedTests: 0
      },
      {
        id: 'user-experience',
        name: 'User Experience Tests',
        description: 'Tests multi-agent workflows and user interactions',
        tests: [
          { id: '9', name: 'Multi-Agent Workflows', status: 'pending', timestamp: new Date().toISOString() },
          { id: '10', name: 'Business Type Customization', status: 'pending', timestamp: new Date().toISOString() },
          { id: '11', name: 'Intelligent Discovery Features', status: 'pending', timestamp: new Date().toISOString() },
          { id: '12', name: 'New User Onboarding', status: 'pending', timestamp: new Date().toISOString() },
          { id: '13', name: 'Complex Issue Resolution', status: 'pending', timestamp: new Date().toISOString() },
          { id: '14', name: 'Agent Handoff Scenarios', status: 'pending', timestamp: new Date().toISOString() }
        ],
        status: 'pending',
        totalTests: 6,
        passedTests: 0,
        failedTests: 0,
        skippedTests: 0
      },
      {
        id: 'performance',
        name: 'Performance Tests',
        description: 'Tests system performance under load',
        tests: [
          { id: '15', name: 'Bulk Rule Evaluation', status: 'pending', timestamp: new Date().toISOString() },
          { id: '16', name: 'Multiple Agent Processing', status: 'pending', timestamp: new Date().toISOString() },
          { id: '17', name: 'Large Dataset Handling', status: 'pending', timestamp: new Date().toISOString() },
          { id: '18', name: 'Concurrent User Simulation', status: 'pending', timestamp: new Date().toISOString() }
        ],
        status: 'pending',
        totalTests: 4,
        passedTests: 0,
        failedTests: 0,
        skippedTests: 0
      }
    ]
    setTestSuites(suites)
  }

  const checkSystemHealth = async () => {
    try {
      // Simulate health check
      const health: SystemHealth = {
        database: 'healthy',
        api: 'healthy',
        ai_services: 'healthy',
        background_tasks: 'healthy'
      }
      
      // Randomly introduce some warnings for testing
      if (Math.random() > 0.8) {
        health.background_tasks = 'warning'
      }
      
      setSystemHealth(health)
    } catch (error) {
      console.error('Health check failed:', error)
    }
  }

  const runTestSuite = async (suiteId: string) => {
    setIsRunningTests(true)
    setActiveTestSuite(suiteId)
    
    const suite = testSuites.find(s => s.id === suiteId)
    if (!suite) return
    
    // Update suite status
    setTestSuites(prev => prev.map(s => 
      s.id === suiteId ? { ...s, status: 'running' } : s
    ))
    
    // Simulate running tests
    for (const test of suite.tests) {
      await runSingleTest(suiteId, test.id)
      await new Promise(resolve => setTimeout(resolve, 1000)) // Simulate test execution time
    }
    
    // Mark suite as completed
    setTestSuites(prev => prev.map(s => 
      s.id === suiteId ? { ...s, status: 'completed' } : s
    ))
    
    setActiveTestSuite(null)
    setIsRunningTests(false)
  }

  const runSingleTest = async (suiteId: string, testId: string) => {
    // Simulate test execution
    const testDuration = Math.random() * 2000 + 500 // 0.5 to 2.5 seconds
    const testPassed = Math.random() > 0.2 // 80% pass rate
    
    setTestSuites(prev => prev.map(suite => {
      if (suite.id === suiteId) {
        const updatedTests = suite.tests.map(test => {
          if (test.id === testId) {
            const status = testPassed ? 'passed' : 'failed'
            const result: TestResult = {
              ...test,
              status,
              duration: testDuration,
              error: testPassed ? undefined : 'Simulated test failure',
              timestamp: new Date().toISOString()
            }
            return result
          }
          return test
        })
        
        const passedTests = updatedTests.filter(t => t.status === 'passed').length
        const failedTests = updatedTests.filter(t => t.status === 'failed').length
        const skippedTests = updatedTests.filter(t => t.status === 'skipped').length
        
        return {
          ...suite,
          tests: updatedTests,
          passedTests,
          failedTests,
          skippedTests
        }
      }
      return suite
    }))
  }

  const runAllTests = async () => {
    setIsRunningTests(true)
    
    for (const suite of testSuites) {
      await runTestSuite(suite.id)
    }
    
    setIsRunningTests(false)
  }

  const resetTests = () => {
    initializeTestSuites()
    setSystemHealth({
      database: 'healthy',
      api: 'healthy',
      ai_services: 'healthy',
      background_tasks: 'healthy'
    })
  }

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'passed':
        return <CheckCircle className="w-4 h-4 text-green-500" />
      case 'failed':
        return <XCircle className="w-4 h-4 text-red-500" />
      case 'running':
        return <Clock className="w-4 h-4 text-blue-500" />
      case 'skipped':
        return <AlertTriangle className="w-4 h-4 text-yellow-500" />
      default:
        return <Clock className="w-4 h-4 text-gray-400" />
    }
  }

  const getStatusBadge = (status: string) => {
    const variants: Record<string, string> = {
      'healthy': 'bg-green-100 text-green-800',
      'warning': 'bg-yellow-100 text-yellow-800',
      'critical': 'bg-red-100 text-red-800'
    }
    
    return (
      <Badge className={variants[status] || 'bg-gray-100 text-gray-800'}>
        {status.charAt(0).toUpperCase() + status.slice(1)}
      </Badge>
    )
  }

  const getHealthIcon = (status: string) => {
    switch (status) {
      case 'healthy':
        return <CheckCircle className="w-5 h-5 text-green-500" />
      case 'warning':
        return <AlertTriangle className="w-5 h-5 text-yellow-500" />
      case 'critical':
        return <XCircle className="w-5 h-5 text-red-500" />
      default:
        return <Clock className="w-5 h-5 text-gray-400" />
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">Phase 6: Testing Dashboard</h1>
          <p className="text-gray-600">Comprehensive system integration and user experience testing</p>
        </div>
        <div className="flex space-x-2">
          <Button 
            onClick={runAllTests} 
            disabled={isRunningTests}
            className="bg-blue-600 hover:bg-blue-700"
          >
            <Play className="w-4 h-4 mr-2" />
            Run All Tests
          </Button>
          <Button 
            onClick={resetTests} 
            variant="outline"
            disabled={isRunningTests}
          >
            <Settings className="w-4 h-4 mr-2" />
            Reset Tests
          </Button>
        </div>
      </div>

      {/* System Health Overview */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center">
            <BarChart3 className="w-5 h-5 mr-2" />
            System Health Overview
          </CardTitle>
          <CardDescription>Current status of all system components</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="flex items-center space-x-3 p-3 border rounded-lg">
              <Database className="w-5 h-5 text-blue-500" />
              <div>
                <p className="text-sm font-medium">Database</p>
                <div className="flex items-center space-x-2">
                  {getHealthIcon(systemHealth.database)}
                  {getStatusBadge(systemHealth.database)}
                </div>
              </div>
            </div>
            
            <div className="flex items-center space-x-3 p-3 border rounded-lg">
              <Zap className="w-5 h-5 text-purple-500" />
              <div>
                <p className="text-sm font-medium">API Services</p>
                <div className="flex items-center space-x-2">
                  {getHealthIcon(systemHealth.api)}
                  {getStatusBadge(systemHealth.api)}
                </div>
              </div>
            </div>
            
            <div className="flex items-center space-x-3 p-3 border rounded-lg">
              <Bot className="w-5 h-5 text-green-500" />
              <div>
                <p className="text-sm font-medium">AI Services</p>
                <div className="flex items-center space-x-2">
                  {getHealthIcon(systemHealth.ai_services)}
                  {getStatusBadge(systemHealth.ai_services)}
                </div>
              </div>
            </div>
            
            <div className="flex items-center space-x-3 p-3 border rounded-lg">
              <Workflow className="w-5 h-5 text-orange-500" />
              <div>
                <p className="text-sm font-medium">Background Tasks</p>
                <div className="flex items-center space-x-2">
                  {getHealthIcon(systemHealth.background_tasks)}
                  {getStatusBadge(systemHealth.background_tasks)}
                </div>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Test Suites */}
      <div className="space-y-4">
        {testSuites.map((suite) => (
          <Card key={suite.id}>
            <CardHeader>
              <div className="flex items-center justify-between">
                <div>
                  <CardTitle className="flex items-center">
                    {suite.status === 'running' ? (
                      <Clock className="w-5 h-5 mr-2 text-blue-500 animate-spin" />
                    ) : suite.status === 'completed' ? (
                      <CheckCircle className="w-5 h-5 mr-2 text-green-500" />
                    ) : (
                      <Clock className="w-5 h-5 mr-2 text-gray-400" />
                    )}
                    {suite.name}
                  </CardTitle>
                  <CardDescription>{suite.description}</CardDescription>
                </div>
                <div className="flex items-center space-x-4">
                  <div className="text-right">
                    <div className="text-sm text-gray-600">
                      {suite.passedTests}/{suite.totalTests} passed
                    </div>
                    <div className="text-xs text-gray-500">
                      {suite.failedTests} failed, {suite.skippedTests} skipped
                    </div>
                  </div>
                  <Button
                    onClick={() => runTestSuite(suite.id)}
                    disabled={isRunningTests || suite.status === 'running'}
                    size="sm"
                  >
                    {suite.status === 'running' ? (
                      <>
                        <Clock className="w-4 h-4 mr-2 animate-spin" />
                        Running...
                      </>
                    ) : (
                      <>
                        <Play className="w-4 h-4 mr-2" />
                        Run Tests
                      </>
                    )}
                  </Button>
                </div>
              </div>
            </CardHeader>
            <CardContent>
              <div className="space-y-2">
                {suite.tests.map((test) => (
                  <div
                    key={test.id}
                    className={`flex items-center justify-between p-3 border rounded-lg ${
                      test.status === 'passed' ? 'border-green-200 bg-green-50' :
                      test.status === 'failed' ? 'border-red-200 bg-red-50' :
                      test.status === 'running' ? 'border-blue-200 bg-blue-50' :
                      'border-gray-200 bg-gray-50'
                    }`}
                  >
                    <div className="flex items-center space-x-3">
                      {getStatusIcon(test.status)}
                      <div>
                        <p className="font-medium">{test.name}</p>
                        {test.error && (
                          <p className="text-sm text-red-600">{test.error}</p>
                        )}
                      </div>
                    </div>
                    <div className="text-right text-sm text-gray-600">
                      {test.duration && (
                        <div>{(test.duration / 1000).toFixed(1)}s</div>
                      )}
                      <div>{new Date(test.timestamp).toLocaleTimeString()}</div>
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Test Summary */}
      {testSuites.some(s => s.status === 'completed') && (
        <Card className="bg-gray-50">
          <CardHeader>
            <CardTitle>Test Summary</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-center">
              <div>
                <div className="text-2xl font-bold text-green-600">
                  {testSuites.reduce((sum, suite) => sum + suite.passedTests, 0)}
                </div>
                <div className="text-sm text-gray-600">Tests Passed</div>
              </div>
              <div>
                <div className="text-2xl font-bold text-red-600">
                  {testSuites.reduce((sum, suite) => sum + suite.failedTests, 0)}
                </div>
                <div className="text-sm text-gray-600">Tests Failed</div>
              </div>
              <div>
                <div className="text-2xl font-bold text-yellow-600">
                  {testSuites.reduce((sum, suite) => sum + suite.skippedTests, 0)}
                </div>
                <div className="text-sm text-gray-600">Tests Skipped</div>
              </div>
              <div>
                <div className="text-2xl font-bold text-blue-600">
                  {testSuites.reduce((sum, suite) => sum + suite.totalTests, 0)}
                </div>
                <div className="text-sm text-gray-600">Total Tests</div>
              </div>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  )
}

export default TestingDashboard

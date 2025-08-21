'use client'

import { useState } from 'react'
import { FileText, Upload, Search, Trash2, Eye } from 'lucide-react'

interface KnowledgeBaseManagerProps {
  workspaceId: string
}

export default function KnowledgeBaseManager({ workspaceId }: KnowledgeBaseManagerProps) {
  const [activeTab, setActiveTab] = useState<'documents' | 'search'>('documents')
  const [searchQuery, setSearchQuery] = useState('')
  const [searchResults, setSearchResults] = useState<any[]>([])
  const [isSearching, setIsSearching] = useState(false)

  // Mock data for demo
  const documents = [
    {
      id: '1',
      title: 'Product Manual v2.1',
      file_type: 'application/pdf',
      file_size: 2048000,
      is_processed: true,
      chunk_count: 45,
      uploaded_at: '2024-01-15T10:30:00Z'
    },
    {
      id: '2',
      title: 'FAQ Document',
      file_type: 'text/plain',
      file_size: 156000,
      is_processed: true,
      chunk_count: 12,
      uploaded_at: '2024-01-14T15:45:00Z'
    },
    {
      id: '3',
      title: 'Company Policies',
      file_type: 'application/pdf',
      file_size: 890000,
      is_processed: false,
      chunk_count: 0,
      uploaded_at: '2024-01-16T09:15:00Z'
    }
  ]

  const handleFileUpload = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0]
    if (file) {
      console.log('File selected:', file.name)
      // In a real app, this would upload the file
    }
  }

  const handleSearch = async () => {
    if (!searchQuery.trim()) return
    
    setIsSearching(true)
    
    // Mock search - in real app this would call the API
    setTimeout(() => {
      setSearchResults([
        {
          id: '1',
          text: 'Our product warranty covers manufacturing defects for a period of 2 years from the date of purchase.',
          document_title: 'Product Manual v2.1',
          similarity_score: 0.92
        },
        {
          id: '2', 
          text: 'For warranty claims, please contact our support team with your purchase receipt and product serial number.',
          document_title: 'Product Manual v2.1',
          similarity_score: 0.87
        }
      ])
      setIsSearching(false)
    }, 1000)
  }

  const formatFileSize = (bytes: number) => {
    if (bytes === 0) return '0 Bytes'
    const k = 1024
    const sizes = ['Bytes', 'KB', 'MB', 'GB']
    const i = Math.floor(Math.log(bytes) / Math.log(k))
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
  }

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h3 className="text-lg font-semibold text-gray-900">Knowledge Base</h3>
        
        {/* Tab Navigation */}
        <div className="flex space-x-1 bg-gray-100 rounded-lg p-1">
          <button
            onClick={() => setActiveTab('documents')}
            className={`px-3 py-1.5 text-sm rounded-md transition-colors ${
              activeTab === 'documents'
                ? 'bg-white text-gray-900 shadow-sm'
                : 'text-gray-600 hover:text-gray-900'
            }`}
          >
            Documents
          </button>
          <button
            onClick={() => setActiveTab('search')}
            className={`px-3 py-1.5 text-sm rounded-md transition-colors ${
              activeTab === 'search'
                ? 'bg-white text-gray-900 shadow-sm'
                : 'text-gray-600 hover:text-gray-900'
            }`}
          >
            Search
          </button>
        </div>
      </div>

      {activeTab === 'documents' && (
        <div className="space-y-6">
          {/* Upload Area */}
          <div className="border-2 border-dashed border-gray-300 rounded-lg p-6">
            <div className="text-center">
              <Upload className="mx-auto h-12 w-12 text-gray-400" />
              <div className="mt-4">
                <label htmlFor="file-upload" className="cursor-pointer">
                  <span className="mt-2 block text-sm font-medium text-gray-900">
                    Upload documents to knowledge base
                  </span>
                  <span className="mt-1 block text-sm text-gray-500">
                    PDF, DOC, TXT files up to 10MB
                  </span>
                </label>
                <input
                  id="file-upload"
                  name="file-upload"
                  type="file"
                  className="sr-only"
                  accept=".pdf,.doc,.docx,.txt"
                  onChange={handleFileUpload}
                />
              </div>
              <div className="mt-6">
                <button
                  type="button"
                  className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-blue-600 hover:bg-blue-700"
                  onClick={() => document.getElementById('file-upload')?.click()}
                >
                  <Upload className="w-4 h-4 mr-2" />
                  Choose Files
                </button>
              </div>
            </div>
          </div>

          {/* Documents List */}
          <div className="bg-white border border-gray-200 rounded-lg">
            <div className="px-6 py-4 border-b border-gray-200">
              <h4 className="text-sm font-medium text-gray-900">
                Uploaded Documents ({documents.length})
              </h4>
            </div>
            <div className="divide-y divide-gray-200">
              {documents.map((doc) => (
                <div key={doc.id} className="px-6 py-4 flex items-center justify-between">
                  <div className="flex items-center space-x-3">
                    <FileText className="w-5 h-5 text-gray-400" />
                    <div>
                      <p className="text-sm font-medium text-gray-900">{doc.title}</p>
                      <div className="flex items-center space-x-4 mt-1">
                        <span className="text-xs text-gray-500">
                          {formatFileSize(doc.file_size)}
                        </span>
                        <span className="text-xs text-gray-500">
                          {doc.chunk_count} chunks
                        </span>
                        <span className={`inline-flex items-center px-2 py-1 rounded text-xs font-medium ${
                          doc.is_processed
                            ? 'bg-green-100 text-green-800'
                            : 'bg-yellow-100 text-yellow-800'
                        }`}>
                          {doc.is_processed ? 'Processed' : 'Processing'}
                        </span>
                      </div>
                    </div>
                  </div>
                  <div className="flex items-center space-x-2">
                    <button className="p-1 text-gray-400 hover:text-gray-600">
                      <Eye className="w-4 h-4" />
                    </button>
                    <button className="p-1 text-gray-400 hover:text-red-600">
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {activeTab === 'search' && (
        <div className="space-y-6">
          {/* Search Interface */}
          <div className="flex space-x-4">
            <div className="flex-1">
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
                placeholder="Search knowledge base..."
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              />
            </div>
            <button
              onClick={handleSearch}
              disabled={isSearching || !searchQuery.trim()}
              className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center"
            >
              {isSearching ? (
                <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin mr-2"></div>
              ) : (
                <Search className="w-4 h-4 mr-2" />
              )}
              Search
            </button>
          </div>

          {/* Search Results */}
          {searchResults.length > 0 && (
            <div className="space-y-4">
              <h4 className="text-sm font-medium text-gray-900">
                Search Results ({searchResults.length})
              </h4>
              {searchResults.map((result) => (
                <div key={result.id} className="bg-white border border-gray-200 rounded-lg p-4">
                  <div className="flex justify-between items-start mb-2">
                    <span className="text-xs font-medium text-blue-600">
                      {result.document_title}
                    </span>
                    <span className="text-xs text-gray-500">
                      {Math.round(result.similarity_score * 100)}% match
                    </span>
                  </div>
                  <p className="text-sm text-gray-900">{result.text}</p>
                </div>
              ))}
            </div>
          )}

          {searchQuery && searchResults.length === 0 && !isSearching && (
            <div className="text-center py-8">
              <Search className="w-12 h-12 text-gray-400 mx-auto mb-4" />
              <p className="text-gray-500">No results found for "{searchQuery}"</p>
            </div>
          )}
        </div>
      )}
    </div>
  )
}


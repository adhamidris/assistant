'use client'

import { useState, useEffect } from 'react'
import { User, Phone, Mail, Calendar, MessageSquare } from 'lucide-react'
import { getContacts } from '@/lib/api'
import { formatRelativeTime } from '@/lib/utils'

interface ContactListProps {
  workspaceId: string
}

interface Contact {
  id: string
  name: string
  masked_phone: string
  email?: string
  created_at: string
  updated_at: string
}

export default function ContactList({ workspaceId }: ContactListProps) {
  const [contacts, setContacts] = useState<Contact[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [searchTerm, setSearchTerm] = useState('')

  useEffect(() => {
    loadContacts()
  }, [workspaceId])

  const loadContacts = async () => {
    try {
      setIsLoading(true)
      const data = await getContacts(workspaceId)
      setContacts(data.results || data)
    } catch (error) {
      console.error('Failed to load contacts:', error)
      setContacts([])
    } finally {
      setIsLoading(false)
    }
  }

  const filteredContacts = contacts.filter(contact =>
    contact.name?.toLowerCase().includes(searchTerm.toLowerCase()) ||
    contact.email?.toLowerCase().includes(searchTerm.toLowerCase()) ||
    contact.masked_phone.includes(searchTerm)
  )

  if (isLoading) {
    return (
      <div className="text-center py-8">
        <div className="w-6 h-6 border-2 border-blue-600 border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
        <p className="text-gray-600">Loading contacts...</p>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h3 className="text-lg font-semibold text-gray-900">Contacts</h3>
        
        {/* Search */}
        <div className="w-72">
          <input
            type="text"
            placeholder="Search contacts..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          />
        </div>
      </div>

      {filteredContacts.length === 0 ? (
        <div className="text-center py-12">
          <User className="w-12 h-12 text-gray-400 mx-auto mb-4" />
          <p className="text-gray-500">
            {searchTerm ? 'No contacts found matching your search' : 'No contacts yet'}
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {filteredContacts.map((contact) => (
            <div key={contact.id} className="bg-white border border-gray-200 rounded-lg p-4 hover:shadow-md transition-shadow">
              <div className="flex items-start space-x-3">
                <div className="w-12 h-12 bg-gray-100 rounded-full flex items-center justify-center">
                  <User className="w-6 h-6 text-gray-600" />
                </div>
                <div className="flex-1 min-w-0">
                  <h4 className="text-sm font-medium text-gray-900 truncate">
                    {contact.name || 'Unknown Contact'}
                  </h4>
                  
                  <div className="mt-2 space-y-1">
                    <div className="flex items-center text-xs text-gray-500">
                      <Phone className="w-3 h-3 mr-1" />
                      <span>{contact.masked_phone}</span>
                    </div>
                    
                    {contact.email && (
                      <div className="flex items-center text-xs text-gray-500">
                        <Mail className="w-3 h-3 mr-1" />
                        <span className="truncate">{contact.email}</span>
                      </div>
                    )}
                    
                    <div className="flex items-center text-xs text-gray-500">
                      <Calendar className="w-3 h-3 mr-1" />
                      <span>Joined {formatRelativeTime(contact.created_at)}</span>
                    </div>
                  </div>
                  
                  <div className="mt-3 flex space-x-2">
                    <button className="flex items-center text-xs text-blue-600 hover:text-blue-800">
                      <MessageSquare className="w-3 h-3 mr-1" />
                      View Chats
                    </button>
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}


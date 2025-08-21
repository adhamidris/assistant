'use client'

import React from 'react'
import { Calendar, Clock, User, MapPin, CheckCircle, AlertCircle } from 'lucide-react'

interface Appointment {
  id: string
  title: string
  description: string
  start_time: string
  end_time: string
  status: string
  contact: {
    name: string
    phone_e164: string
  }
  customer_notes?: string
  location_type?: string
}

interface AppointmentsListProps {
  appointments: Appointment[]
}

export default function AppointmentsList({ appointments }: AppointmentsListProps) {
  const formatDateTime = (dateTimeString: string) => {
    const date = new Date(dateTimeString)
    return {
      date: date.toLocaleDateString('en-US', { 
        weekday: 'long', 
        year: 'numeric', 
        month: 'long', 
        day: 'numeric' 
      }),
      time: date.toLocaleTimeString('en-US', { 
        hour: 'numeric', 
        minute: '2-digit',
        hour12: true 
      })
    }
  }

  const getStatusIcon = (status: string) => {
    switch (status.toLowerCase()) {
      case 'confirmed':
        return <CheckCircle className="w-4 h-4 text-green-500" />
      case 'pending':
        return <Clock className="w-4 h-4 text-yellow-500" />
      case 'cancelled':
        return <AlertCircle className="w-4 h-4 text-red-500" />
      default:
        return <Calendar className="w-4 h-4 text-blue-500" />
    }
  }

  const getStatusColor = (status: string) => {
    switch (status.toLowerCase()) {
      case 'confirmed':
        return 'bg-green-100 text-green-800'
      case 'pending':
        return 'bg-yellow-100 text-yellow-800'
      case 'cancelled':
        return 'bg-red-100 text-red-800'
      default:
        return 'bg-blue-100 text-blue-800'
    }
  }

  if (appointments.length === 0) {
    return (
      <div className="text-center py-12">
        <Calendar className="w-16 h-16 text-gray-300 mx-auto mb-4" />
        <h3 className="text-lg font-semibold text-gray-900 mb-2">No Appointments Yet</h3>
        <p className="text-gray-500 max-w-md mx-auto">
          When customers book appointments through your AI assistant, they'll appear here.
        </p>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-gray-900">Appointments</h2>
          <p className="text-gray-600">Manage your scheduled appointments</p>
        </div>
        <div className="text-sm text-gray-500">
          {appointments.length} appointment{appointments.length !== 1 ? 's' : ''}
        </div>
      </div>

      <div className="grid gap-4">
        {appointments.map((appointment) => {
          const { date, time } = formatDateTime(appointment.start_time)
          const endTime = formatDateTime(appointment.end_time).time

          return (
            <div
              key={appointment.id}
              className="bg-white rounded-lg border border-gray-200 p-6 hover:shadow-md transition-shadow"
            >
              <div className="flex items-start justify-between mb-4">
                <div className="flex-1">
                  <div className="flex items-center space-x-2 mb-2">
                    <h3 className="text-lg font-semibold text-gray-900">
                      {appointment.title}
                    </h3>
                    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${getStatusColor(appointment.status)}`}>
                      {getStatusIcon(appointment.status)}
                      <span className="ml-1">{appointment.status}</span>
                    </span>
                  </div>
                  {appointment.description && (
                    <p className="text-gray-600 mb-3">{appointment.description}</p>
                  )}
                </div>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
                <div className="flex items-center space-x-2">
                  <Calendar className="w-4 h-4 text-gray-400" />
                  <span className="text-sm text-gray-600">{date}</span>
                </div>
                <div className="flex items-center space-x-2">
                  <Clock className="w-4 h-4 text-gray-400" />
                  <span className="text-sm text-gray-600">{time} - {endTime}</span>
                </div>
                <div className="flex items-center space-x-2">
                  <User className="w-4 h-4 text-gray-400" />
                  <span className="text-sm text-gray-600">
                    {appointment.contact?.name || 'Unknown'} ({appointment.contact?.phone_e164})
                  </span>
                </div>
                {appointment.location_type && (
                  <div className="flex items-center space-x-2">
                    <MapPin className="w-4 h-4 text-gray-400" />
                    <span className="text-sm text-gray-600 capitalize">
                      {appointment.location_type.replace('_', ' ')}
                    </span>
                  </div>
                )}
              </div>

              {appointment.customer_notes && (
                <div className="mt-4 pt-4 border-t border-gray-100">
                  <p className="text-sm text-gray-600">
                    <span className="font-medium">Notes:</span> {appointment.customer_notes}
                  </p>
                </div>
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}

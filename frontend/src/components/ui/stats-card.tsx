import React from 'react'
import { cn } from '@/lib/utils'
import { LucideIcon } from 'lucide-react'

interface StatsCardProps {
  title: string
  value: string | number
  icon: LucideIcon
  color: 'blue' | 'green' | 'yellow' | 'purple' | 'red' | 'indigo'
  change: string
  trend?: 'up' | 'down' | 'neutral'
  className?: string
}

const StatsCard: React.FC<StatsCardProps> = ({
  title,
  value,
  icon: Icon,
  color,
  change,
  trend = 'neutral',
  className
}) => {
  const colorClasses = {
    blue: 'bg-blue-100 text-blue-600',
    green: 'bg-green-100 text-green-600',
    yellow: 'bg-yellow-100 text-yellow-600',
    purple: 'bg-purple-100 text-purple-600',
    red: 'bg-red-100 text-red-600',
    indigo: 'bg-indigo-100 text-indigo-600'
  }

  const trendColors = {
    up: 'text-green-600',
    down: 'text-red-600',
    neutral: 'text-gray-600'
  }

  return (
    <div className={cn(
      'bg-white rounded-xl shadow-sm border border-gray-200 p-6 hover:shadow-md transition-all duration-200 group',
      className
    )}>
      <div className="flex items-center justify-between">
        <div className="flex-1">
          <p className="text-sm font-medium text-gray-600 mb-1">{title}</p>
          <p className="text-2xl font-bold text-gray-900">{value}</p>
        </div>
        <div className={cn(
          'w-12 h-12 rounded-lg flex items-center justify-center transition-transform group-hover:scale-110',
          colorClasses[color]
        )}>
          <Icon className="w-6 h-6" />
        </div>
      </div>
      
      <div className="mt-4 flex items-center space-x-2">
        <span className={cn('text-sm font-medium', trendColors[trend])}>
          {change}
        </span>
        {trend !== 'neutral' && (
          <div className={cn(
            'w-2 h-2 rounded-full',
            trend === 'up' ? 'bg-green-400' : 'bg-red-400'
          )} />
        )}
      </div>
    </div>
  )
}

export default StatsCard

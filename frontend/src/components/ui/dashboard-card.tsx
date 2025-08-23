import React from 'react'
import { cn } from '@/lib/utils'

interface DashboardCardProps {
  children: React.ReactNode
  className?: string
  variant?: 'default' | 'gradient' | 'outlined'
  size?: 'sm' | 'md' | 'lg'
  hover?: boolean
}

const DashboardCard: React.FC<DashboardCardProps> = ({
  children,
  className,
  variant = 'default',
  size = 'md',
  hover = true
}) => {
  const baseClasses = 'rounded-xl border transition-all duration-200'
  
  const variantClasses = {
    default: 'bg-white border-gray-200 shadow-sm',
    gradient: 'bg-gradient-to-br from-blue-50 to-purple-50 border-blue-200 shadow-sm',
    outlined: 'bg-transparent border-gray-300 shadow-none'
  }
  
  const sizeClasses = {
    sm: 'p-4',
    md: 'p-6',
    lg: 'p-8'
  }
  
  const hoverClasses = hover ? 'hover:shadow-md hover:border-gray-300' : ''
  
  return (
    <div className={cn(
      baseClasses,
      variantClasses[variant],
      sizeClasses[size],
      hoverClasses,
      className
    )}>
      {children}
    </div>
  )
}

export default DashboardCard

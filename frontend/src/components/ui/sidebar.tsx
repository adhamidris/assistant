import React from 'react'
import { cn } from '@/lib/utils'
import { ChevronLeft, ChevronRight } from 'lucide-react'

interface SidebarProps {
  children: React.ReactNode
  collapsed: boolean
  onToggle: () => void
  className?: string
}

const Sidebar: React.FC<SidebarProps> = ({
  children,
  collapsed,
  onToggle,
  className
}) => {
  return (
    <div className={cn(
      'bg-white shadow-lg transition-all duration-300 ease-in-out relative',
      collapsed ? 'w-16' : 'w-64',
      className
    )}>
      {/* Toggle Button */}
      <button
        onClick={onToggle}
        className="absolute -right-3 top-6 w-6 h-6 bg-white border border-gray-200 rounded-full shadow-sm flex items-center justify-center hover:shadow-md transition-shadow z-10"
      >
        {collapsed ? (
          <ChevronRight className="w-3 h-3 text-gray-600" />
        ) : (
          <ChevronLeft className="w-3 h-3 text-gray-600" />
        )}
      </button>
      
      {children}
    </div>
  )
}

export default Sidebar

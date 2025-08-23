import React from 'react'
import { cn } from '@/lib/utils'
import { LucideIcon } from 'lucide-react'

interface NavItemProps {
  icon: LucideIcon
  label: string
  badge?: number
  active?: boolean
  collapsed?: boolean
  onClick: () => void
  className?: string
}

const NavItem: React.FC<NavItemProps> = ({
  icon: Icon,
  label,
  badge,
  active = false,
  collapsed = false,
  onClick,
  className
}) => {
  return (
    <button
      onClick={onClick}
      className={cn(
        'w-full flex items-center space-x-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-all duration-200 relative group',
        active
          ? 'bg-blue-50 text-blue-700 border border-blue-200 shadow-sm'
          : 'text-gray-700 hover:bg-gray-50 hover:text-gray-900',
        collapsed ? 'justify-center' : '',
        className
      )}
    >
      <Icon className={cn(
        'w-5 h-5 transition-colors',
        active ? 'text-blue-600' : 'text-gray-500 group-hover:text-gray-700'
      )} />
      
      {!collapsed && (
        <>
          <span className="flex-1 text-left">{label}</span>
          {badge !== undefined && (
            <span className={cn(
              'px-2 py-1 text-xs rounded-full font-medium transition-colors',
              active
                ? 'bg-blue-100 text-blue-700'
                : 'bg-gray-100 text-gray-600 group-hover:bg-gray-200'
            )}>
              {badge}
            </span>
          )}
        </>
      )}
      
      {/* Active indicator for collapsed state */}
      {collapsed && active && (
        <div className="absolute -right-1 top-1/2 -translate-y-1/2 w-1 h-8 bg-blue-600 rounded-l-full" />
      )}
    </button>
  )
}

export default NavItem

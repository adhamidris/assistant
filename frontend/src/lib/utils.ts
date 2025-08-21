import { type ClassValue, clsx } from 'clsx'
import { twMerge } from 'tailwind-merge'
import { format, formatDistanceToNow, isToday, isYesterday } from 'date-fns'

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

// Phone number formatting
export function formatPhoneNumber(phone: string): string {
  // Remove all non-digit characters
  const cleaned = phone.replace(/\D/g, '')
  
  // Format as (XXX) XXX-XXXX for US numbers
  if (cleaned.length === 10) {
    return `(${cleaned.slice(0, 3)}) ${cleaned.slice(3, 6)}-${cleaned.slice(6)}`
  }
  
  // Format international numbers with country code
  if (cleaned.length > 10) {
    const countryCode = cleaned.slice(0, cleaned.length - 10)
    const number = cleaned.slice(-10)
    return `+${countryCode} (${number.slice(0, 3)}) ${number.slice(3, 6)}-${number.slice(6)}`
  }
  
  return phone
}

// Enhanced phone validation for international numbers
export function isValidPhoneNumber(phone: string): boolean {
  const cleaned = phone.replace(/\D/g, '')
  
  // Check basic length requirements
  if (cleaned.length < 7 || cleaned.length > 15) {
    return false
  }
  
  // If it starts with +, validate international format
  if (phone.trim().startsWith('+')) {
    return cleaned.length >= 10 && cleaned.length <= 15
  }
  
  // Egyptian mobile numbers are typically 10-11 digits (with or without leading 0)
  if (cleaned.length >= 10 && cleaned.length <= 11) {
    return true
  }
  
  // US numbers (10 digits)
  if (cleaned.length === 10) {
    return true
  }
  
  return false
}

// Format phone to E.164 format with Egyptian number support
export function toE164Format(phone: string, defaultCountryCode = '20'): string {
  let cleaned = phone.replace(/\D/g, '')
  
  // If already has + and looks valid, return formatted
  if (phone.trim().startsWith('+') && cleaned.length >= 10 && cleaned.length <= 15) {
    return `+${cleaned}`
  }
  
  // Handle Egyptian mobile numbers (typically 10-11 digits)
  if (cleaned.length === 10 || cleaned.length === 11) {
    // Remove leading 0 if present (common in Egyptian numbers)
    if (cleaned.startsWith('0')) {
      cleaned = cleaned.substring(1)
    }
    // Default to Egypt country code for 10-11 digit numbers
    return `+20${cleaned}`
  }
  
  // Handle US numbers (exactly 10 digits, likely US)
  if (cleaned.length === 10 && defaultCountryCode === '1') {
    return `+1${cleaned}`
  }
  
  // For other lengths, add country code if missing
  if (cleaned.length > 10 && !phone.trim().startsWith('+')) {
    return `+${cleaned}`
  }
  
  // Fallback: add default country code
  return `+${defaultCountryCode}${cleaned}`
}

// Date formatting utilities
export function formatMessageTime(dateString: string): string {
  const date = new Date(dateString)
  const now = new Date()
  
  if (isToday(date)) {
    return format(date, 'h:mm a')
  } else if (isYesterday(date)) {
    return 'Yesterday'
  } else if (date.getFullYear() === now.getFullYear()) {
    return format(date, 'MMM d')
  } else {
    return format(date, 'MMM d, yyyy')
  }
}

export function formatRelativeTime(dateString: string): string {
  const date = new Date(dateString)
  return formatDistanceToNow(date, { addSuffix: true })
}

export function formatFullDateTime(dateString: string): string {
  const date = new Date(dateString)
  return format(date, 'PPP p') // e.g., "January 1st, 2024 at 12:00 PM"
}

// File size formatting
export function formatFileSize(bytes: number): string {
  if (bytes === 0) return '0 Bytes'
  
  const k = 1024
  const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
}

// Message type utilities
export function getMessageIcon(messageType: string): string {
  switch (messageType) {
    case 'text':
      return '💬'
    case 'audio':
      return '🎵'
    case 'file':
      return '📎'
    case 'system':
      return 'ℹ️'
    default:
      return '💬'
  }
}

export function getMessageTypeLabel(messageType: string): string {
  switch (messageType) {
    case 'text':
      return 'Text'
    case 'audio':
      return 'Audio'
    case 'file':
      return 'File'
    case 'system':
      return 'System'
    default:
      return 'Message'
  }
}

// Status utilities
export function getStatusColor(status: string): string {
  switch (status) {
    case 'sending':
      return 'text-yellow-600'
    case 'sent':
      return 'text-green-600'
    case 'processing':
      return 'text-blue-600'
    case 'processed':
      return 'text-green-600'
    case 'failed':
      return 'text-red-600'
    default:
      return 'text-gray-600'
  }
}

export function getStatusIcon(status: string): string {
  switch (status) {
    case 'sending':
      return '⏳'
    case 'sent':
      return '✓'
    case 'processing':
      return '⚡'
    case 'processed':
      return '✅'
    case 'failed':
      return '❌'
    default:
      return '○'
  }
}

// React component version for use in components
export function getStatusIconComponent(status: string) {
  // This function should be used in .tsx files only
  // For .ts files, use getStatusIcon instead
  return getStatusIcon(status)
}

// Intent classification utilities
export function getIntentColor(intent: string): string {
  switch (intent) {
    case 'inquiry':
      return 'bg-blue-100 text-blue-800'
    case 'request':
      return 'bg-green-100 text-green-800'
    case 'complaint':
      return 'bg-red-100 text-red-800'
    case 'appointment':
      return 'bg-purple-100 text-purple-800'
    case 'other':
      return 'bg-gray-100 text-gray-800'
    default:
      return 'bg-gray-100 text-gray-800'
  }
}

export function getIntentLabel(intent: string): string {
  switch (intent) {
    case 'inquiry':
      return 'Question'
    case 'request':
      return 'Request'
    case 'complaint':
      return 'Issue'
    case 'appointment':
      return 'Appointment'
    case 'other':
      return 'General'
    default:
      return intent || 'Unknown'
  }
}

// Text utilities
export function truncateText(text: string, maxLength: number): string {
  if (text.length <= maxLength) return text
  return text.slice(0, maxLength).trim() + '...'
}

export function highlightSearchTerms(text: string, searchTerm: string): string {
  if (!searchTerm) return text
  
  const regex = new RegExp(`(${searchTerm})`, 'gi')
  return text.replace(regex, '<mark class="bg-yellow-200">$1</mark>')
}

// Validation utilities
export function isValidEmail(email: string): boolean {
  const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
  return emailRegex.test(email)
}

export function isValidUrl(url: string): boolean {
  try {
    new URL(url)
    return true
  } catch {
    return false
  }
}

// Local storage utilities with error handling
export function getLocalStorageItem(key: string): string | null {
  try {
    if (typeof window === 'undefined') return null
    return localStorage.getItem(key)
  } catch (error) {
    console.warn(`Error reading localStorage key "${key}":`, error)
    return null
  }
}

export function setLocalStorageItem(key: string, value: string): boolean {
  try {
    if (typeof window === 'undefined') return false
    localStorage.setItem(key, value)
    return true
  } catch (error) {
    console.warn(`Error setting localStorage key "${key}":`, error)
    return false
  }
}

export function removeLocalStorageItem(key: string): boolean {
  try {
    if (typeof window === 'undefined') return false
    localStorage.removeItem(key)
    return true
  } catch (error) {
    console.warn(`Error removing localStorage key "${key}":`, error)
    return false
  }
}

// Error handling utilities
export function getErrorMessage(error: any): string {
  if (typeof error === 'string') return error
  
  if (error?.response?.data?.error) {
    return error.response.data.error
  }
  
  if (error?.response?.data?.message) {
    return error.response.data.message
  }
  
  if (error?.message) {
    return error.message
  }
  
  return 'An unexpected error occurred'
}

// Audio utilities
export function formatDuration(seconds: number): string {
  const minutes = Math.floor(seconds / 60)
  const remainingSeconds = Math.floor(seconds % 60)
  return `${minutes}:${remainingSeconds.toString().padStart(2, '0')}`
}

// Workspace utilities
export function generateWorkspaceId(): string {
  // For demo purposes - in production this would come from the backend
  return 'demo-workspace-' + Math.random().toString(36).substr(2, 9)
}

// Debounce utility
export function debounce<T extends (...args: any[]) => any>(
  func: T,
  wait: number
): (...args: Parameters<T>) => void {
  let timeout: NodeJS.Timeout | null = null
  
  return (...args: Parameters<T>) => {
    if (timeout) clearTimeout(timeout)
    timeout = setTimeout(() => func(...args), wait)
  }
}

// Copy to clipboard utility
export async function copyToClipboard(text: string): Promise<boolean> {
  try {
    if (navigator.clipboard && window.isSecureContext) {
      await navigator.clipboard.writeText(text)
      return true
    } else {
      // Fallback for older browsers
      const textArea = document.createElement('textarea')
      textArea.value = text
      textArea.style.position = 'fixed'
      textArea.style.left = '-999999px'
      textArea.style.top = '-999999px'
      document.body.appendChild(textArea)
      textArea.focus()
      textArea.select()
      const result = document.execCommand('copy')
      textArea.remove()
      return result
    }
  } catch (error) {
    console.error('Failed to copy text:', error)
    return false
  }
}


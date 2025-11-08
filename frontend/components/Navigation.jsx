'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'

/**
 * Navigation component for Kora
 */
export default function Navigation() {
  const pathname = usePathname()

  const navItems = [
    { href: '/', label: 'Home', icon: '🏠' },
    { href: '/live', label: 'Live', icon: '📹' },
    { href: '/settings', label: 'Settings', icon: '⚙️' },
    { href: '/help', label: 'Help', icon: '❓' },
  ]

  return (
    <nav className="glass-panel p-4">
      <div className="flex items-center justify-between max-w-7xl mx-auto">
        <div className="flex items-center space-x-2">
          <div className="text-2xl font-bold bg-gradient-to-r from-kora-blue to-kora-cyan bg-clip-text text-transparent">
            KORA
          </div>
        </div>

        <div className="flex space-x-1">
          {navItems.map(item => {
            const isActive = pathname === item.href
            return (
              <Link
                key={item.href}
                href={item.href}
                className={`
                  px-4 py-2 rounded-lg transition-all duration-200
                  ${isActive
                    ? 'bg-kora-gradient text-white shadow-kora-glow'
                    : 'text-gray-400 hover:text-white hover:bg-kora-panel'
                  }
                `}
              >
                <span className="mr-2">{item.icon}</span>
                <span className="hidden sm:inline">{item.label}</span>
              </Link>
            )
          })}
        </div>
      </div>
    </nav>
  )
}

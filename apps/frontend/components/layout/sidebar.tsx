'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { LayoutDashboard, Users, FileText, MessageSquare } from 'lucide-react'
import { cn } from '@/lib/utils'

const nav = [
  { href: '/dashboard', icon: LayoutDashboard, label: 'Dashboard' },
  { href: '/employees', icon: Users, label: 'Empleados' },
  { href: '/documents', icon: FileText, label: 'Documentos' },
  { href: '/chat', icon: MessageSquare, label: 'Asistente IA' },
]

export function Sidebar() {
  const pathname = usePathname()

  return (
    <aside className="flex h-full w-56 flex-col border-r bg-card">
      <div className="flex h-14 items-center border-b px-4">
        <span className="font-bold text-lg tracking-tight">Kuaai HRMS</span>
      </div>
      <nav className="flex-1 space-y-0.5 p-3">
        {nav.map(({ href, icon: Icon, label }) => (
          <Link
            key={href}
            href={href}
            className={cn(
              'flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors',
              pathname === href || pathname.startsWith(href + '/')
                ? 'bg-primary text-primary-foreground'
                : 'text-muted-foreground hover:bg-muted hover:text-foreground',
            )}
          >
            <Icon className="size-4 shrink-0" />
            {label}
          </Link>
        ))}
      </nav>
    </aside>
  )
}

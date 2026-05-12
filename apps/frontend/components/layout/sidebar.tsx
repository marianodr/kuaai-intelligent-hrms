'use client'

import Image from 'next/image'
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
    <aside className="flex h-full w-64 flex-col border-r bg-white">
      <div className="flex h-16 items-center border-b px-6 overflow-hidden">
        <Image src="/logo.png" alt="Kuaai Intelligent HRMS" height={36} width={36} className="h-9 w-auto" priority />
      </div>
      <nav className="flex-1 space-y-0.5 p-3">
        {nav.map(({ href, icon: Icon, label }) => (
          <Link
            key={href}
            href={href}
            className={cn(
              'flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors',
              pathname === href || pathname.startsWith(href + '/')
                ? 'bg-primary-light text-primary'
                : 'text-muted-foreground hover:bg-surface hover:text-foreground',
            )}
          >
            <Icon size={20} className="shrink-0" />
            {label}
          </Link>
        ))}
      </nav>
    </aside>
  )
}

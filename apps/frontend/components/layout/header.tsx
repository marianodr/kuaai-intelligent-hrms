'use client'

import { useRouter } from 'next/navigation'
import { LogOut } from 'lucide-react'
import { clearSession, getUser } from '@/lib/auth'
import { Button } from '@/components/ui/button'

export function Header() {
  const router = useRouter()
  const user = getUser()

  function handleLogout() {
    clearSession()
    router.push('/login')
  }

  return (
    <header className="flex h-14 items-center justify-between border-b bg-card px-4">
      <div />
      <div className="flex items-center gap-3">
        {user && (
          <span className="text-sm text-muted-foreground">
            {user.email} · <span className="uppercase font-medium">{user.role}</span>
          </span>
        )}
        <Button variant="ghost" size="icon" onClick={handleLogout} title="Cerrar sesión">
          <LogOut className="size-4" />
        </Button>
      </div>
    </header>
  )
}

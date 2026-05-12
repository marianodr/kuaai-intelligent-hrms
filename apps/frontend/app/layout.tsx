import type { Metadata } from 'next'
import { Geist } from 'next/font/google'
import './globals.css'

const geist = Geist({ subsets: ['latin'], variable: '--font-sans' })

export const metadata: Metadata = {
  title: 'Kuaai HRMS',
  description: 'Sistema Inteligente de Gestión de Recursos Humanos',
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="es" className={`${geist.variable} h-full`}>
      <body className="h-full bg-background text-foreground antialiased">{children}</body>
    </html>
  )
}

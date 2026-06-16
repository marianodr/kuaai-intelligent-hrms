'use client'

import { useEffect, useState } from 'react'
import { getToken } from '@/lib/auth'
import { X } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'

const NEST = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:3001'

interface PdfViewerProps {
  documentId: string
  documentName: string
  onClose: () => void
}

export function PdfViewer({ documentId, documentName, onClose }: PdfViewerProps) {
  const [src, setSrc] = useState<string | null>(null)
  const [error, setError] = useState('')

  useEffect(() => {
    const token = getToken()
    if (!token) {
      setError('No autorizado')
      return
    }
    const url = `${NEST}/documents/${documentId}/download?token=${encodeURIComponent(token)}`
    setSrc(url)
  }, [documentId])

  return (
    <div className={cn(
      'fixed inset-0 z-50 flex flex-col bg-black/60 backdrop-blur-sm',
    )}>
      <div className="flex items-center justify-between bg-white px-4 py-2 shadow">
        <span className="text-sm font-medium truncate max-w-[80vw]">{documentName}</span>
        <Button variant="ghost" size="icon" onClick={onClose}>
          <X />
        </Button>
      </div>

      {error && (
        <div className="flex-1 flex items-center justify-center text-white">
          {error}
        </div>
      )}

      {src && !error && (
        <iframe
          src={src}
          className="flex-1 w-full border-0"
          title={documentName}
        />
      )}
    </div>
  )
}

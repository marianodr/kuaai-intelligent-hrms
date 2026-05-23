'use client'

import React, { useEffect, useState, useRef } from 'react'
import { documentsApi } from '@/lib/api'
import { getUser } from '@/lib/auth'
import { cn } from '@/lib/utils'
import type { Document } from '@/types'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Card } from '@/components/ui/card'
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from '@/components/ui/table'
import { Upload, Trash2, RefreshCw, Check } from 'lucide-react'

// ─── Configuración del pipeline ────────────────────────────────────────────

const PIPELINE_STEPS = [
  { label: 'Descarga',      progress: 'Descargando PDF...' },
  { label: 'Extracción',    progress: 'Extrayendo texto con Docling...' },
  { label: 'Fragmentación', progress: 'Dividiendo en fragmentos...' },
  { label: 'Embeddings',    progress: 'Generando embeddings...' },
]

const STATUS_LABEL: Record<Document['status'], string> = {
  PROCESSING: 'Procesando',
  READY:      'Listo',
  ERROR:      'Error',
}

const STATUS_VARIANT: Record<Document['status'], 'default' | 'secondary' | 'destructive'> = {
  READY:      'default',
  PROCESSING: 'secondary',
  ERROR:      'destructive',
}

// ─── Stepper ───────────────────────────────────────────────────────────────

function ProcessingStepper({ progress }: { progress?: string | null }) {
  const activeStep = PIPELINE_STEPS.findIndex(s => s.progress === progress)
  const current = activeStep === -1 ? 0 : activeStep

  return (
    <div className="flex items-start w-full py-2 px-1">
      {PIPELINE_STEPS.map((step, i) => {
        const completed = i < current
        const active    = i === current
        const pending   = i > current

        return (
          <React.Fragment key={step.label}>
            <div className="flex flex-col items-center gap-1.5 min-w-0">
              {/* Círculo */}
              <div
                className={cn(
                  'w-6 h-6 rounded-full flex items-center justify-center border-2 shrink-0',
                  completed && 'bg-primary border-primary',
                  active    && 'border-primary bg-primary/10 animate-pulse',
                  pending   && 'border-muted-foreground/30 bg-transparent',
                )}
              >
                {completed
                  ? <Check className="w-3 h-3 text-primary-foreground" strokeWidth={3} />
                  : <span className={cn(
                      'w-2 h-2 rounded-full',
                      active  ? 'bg-primary' : 'bg-muted-foreground/25',
                    )} />
                }
              </div>
              {/* Label */}
              <span className={cn(
                'text-xs text-center leading-tight',
                completed && 'text-primary',
                active    && 'text-primary font-medium',
                pending   && 'text-muted-foreground/40',
              )}>
                {step.label}
              </span>
            </div>

            {/* Línea conectora */}
            {i < PIPELINE_STEPS.length - 1 && (
              <div className={cn(
                'h-0.5 flex-1 mt-3 mx-1',
                i < current ? 'bg-primary' : 'bg-muted-foreground/20',
              )} />
            )}
          </React.Fragment>
        )
      })}
    </div>
  )
}

// ─── Página ────────────────────────────────────────────────────────────────

export default function DocumentsPage() {
  const [documents, setDocuments] = useState<Document[]>([])
  const [loading, setLoading]     = useState(true)
  const [uploading, setUploading] = useState(false)
  const [error, setError]         = useState('')
  const fileRef = useRef<HTMLInputElement>(null)
  const user = getUser()

  const hasProcessing = documents.some(d => d.status === 'PROCESSING')

  async function fetchDocuments() {
    setLoading(true)
    try {
      const docs = await documentsApi.list()
      setDocuments(docs)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { fetchDocuments() }, [])

  // Auto-poll cada 3s mientras haya documentos procesando
  useEffect(() => {
    if (!hasProcessing) return
    const id = setInterval(async () => {
      try {
        const docs = await documentsApi.list()
        setDocuments(docs)
      } catch {}
    }, 3000)
    return () => clearInterval(id)
  }, [hasProcessing])

  async function handleUpload(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0]
    if (!file || !user) return
    setUploading(true)
    setError('')
    try {
      const { document_id } = await documentsApi.upload(file, user.id)
      await documentsApi.process(document_id)
      await fetchDocuments()
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Error al subir el archivo')
    } finally {
      setUploading(false)
      if (fileRef.current) fileRef.current.value = ''
    }
  }

  async function handleDelete(id: string, name: string) {
    if (!confirm(`¿Eliminar "${name}"? Esta acción no se puede deshacer.`)) return
    try {
      await documentsApi.delete(id)
      setDocuments(prev => prev.filter(d => d.id !== id))
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Error al eliminar')
    }
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold">Documentos</h1>
        <div className="flex gap-2">
          <Button variant="outline" size="icon" onClick={fetchDocuments} title="Actualizar">
            <RefreshCw className={loading ? 'animate-spin' : ''} />
          </Button>
          <Button onClick={() => fileRef.current?.click()} disabled={uploading}>
            <Upload />
            {uploading ? 'Subiendo...' : 'Subir PDF'}
          </Button>
          <input
            ref={fileRef}
            type="file"
            accept=".pdf"
            className="hidden"
            onChange={handleUpload}
          />
        </div>
      </div>

      {error && <p className="text-sm text-destructive">{error}</p>}

      <Card className="p-0 overflow-hidden">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Nombre</TableHead>
              <TableHead>Estado</TableHead>
              <TableHead>Fecha</TableHead>
              <TableHead className="text-right">Acciones</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {loading ? (
              <TableRow>
                <TableCell colSpan={4} className="text-center text-muted-foreground py-8">
                  Cargando...
                </TableCell>
              </TableRow>
            ) : documents.length === 0 ? (
              <TableRow>
                <TableCell colSpan={4} className="text-center text-muted-foreground py-8">
                  No hay documentos. Subí un PDF para comenzar.
                </TableCell>
              </TableRow>
            ) : (
              documents.map((doc) => (
                <React.Fragment key={doc.id}>
                  <TableRow>
                    <TableCell className="font-medium">{doc.name}</TableCell>
                    <TableCell>
                      <Badge variant={STATUS_VARIANT[doc.status]}>
                        {STATUS_LABEL[doc.status]}
                      </Badge>
                    </TableCell>
                    <TableCell className="text-sm text-muted-foreground">
                      {new Date(doc.created_at).toLocaleString('es-AR')}
                    </TableCell>
                    <TableCell className="text-right">
                      <Button
                        variant="ghost"
                        size="icon"
                        onClick={() => handleDelete(doc.id, doc.name)}
                        disabled={doc.status === 'PROCESSING'}
                      >
                        <Trash2 className="text-destructive" />
                      </Button>
                    </TableCell>
                  </TableRow>

                  {doc.status === 'PROCESSING' && (
                    <TableRow className="bg-muted/30 hover:bg-muted/30">
                      <TableCell colSpan={4} className="py-1 px-6">
                        <ProcessingStepper progress={doc.progress} />
                      </TableCell>
                    </TableRow>
                  )}
                </React.Fragment>
              ))
            )}
          </TableBody>
        </Table>
      </Card>
    </div>
  )
}

'use client'

import { useEffect, useState, useRef } from 'react'
import { documentsApi } from '@/lib/api'
import { getUser } from '@/lib/auth'
import type { Document } from '@/types'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Card } from '@/components/ui/card'
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from '@/components/ui/table'
import { Upload, Trash2, RefreshCw } from 'lucide-react'

const STATUS_VARIANT: Record<Document['status'], 'default' | 'secondary' | 'destructive'> = {
  READY: 'default',
  PROCESSING: 'secondary',
  ERROR: 'destructive',
}

export default function DocumentsPage() {
  const [documents, setDocuments] = useState<Document[]>([])
  const [loading, setLoading] = useState(true)
  const [uploading, setUploading] = useState(false)
  const [error, setError] = useState('')
  const fileRef = useRef<HTMLInputElement>(null)
  const user = getUser()

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
      setDocuments((prev) => prev.filter((d) => d.id !== id))
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

      {error && (
        <p className="text-sm text-destructive">{error}</p>
      )}

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
                <TableRow key={doc.id}>
                  <TableCell className="font-medium">{doc.name}</TableCell>
                  <TableCell>
                    <Badge variant={STATUS_VARIANT[doc.status]}>{doc.status}</Badge>
                  </TableCell>
                  <TableCell className="text-sm text-muted-foreground">
                    {new Date(doc.created_at).toLocaleString('es-AR')}
                  </TableCell>
                  <TableCell className="text-right">
                    <Button
                      variant="ghost"
                      size="icon"
                      onClick={() => handleDelete(doc.id, doc.name)}
                    >
                      <Trash2 className="text-destructive" />
                    </Button>
                  </TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </Card>

      <p className="text-xs text-muted-foreground">
        Los documentos en estado PROCESSING pueden tardar entre 10 y 60 segundos según su tamaño.
        Actualizá la lista para ver el estado final.
      </p>
    </div>
  )
}

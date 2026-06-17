'use client'

import { useEffect, useState, useCallback } from 'react'
import { documentsApi, chunksApi } from '@/lib/api'
import { getUser } from '@/lib/auth'
import type { Document, DocumentChunk, ChunkSearchResult } from '@/types'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'
import { Card } from '@/components/ui/card'
import { Separator } from '@/components/ui/separator'
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from '@/components/ui/table'
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from '@/components/ui/select'
import {
  ShieldAlert, Search, X, ChevronDown, ChevronRight,
  FileText, ScanSearch, Layers,
} from 'lucide-react'

// ─── Similarity badge ──────────────────────────────────────────────────────

function SimilarityBadge({ score }: { score: number }) {
  const pct = Math.round(score * 100)
  const style =
    score >= 0.5
      ? { background: '#ecfdf5', color: '#15803d', borderColor: '#86efac' }
      : score >= 0.3
      ? { background: '#fffbeb', color: '#b45309', borderColor: '#fcd34d' }
      : { background: '#f3f4f6', color: '#6b7280', borderColor: '#e5e7eb' }
  return (
    <span
      className="inline-flex items-center rounded-full border px-2 py-0.5 text-xs font-medium font-mono tabular-nums"
      style={style}
    >
      {pct}%
    </span>
  )
}

// ─── Embedding detail panel ────────────────────────────────────────────────

function EmbeddingDetail({ emb }: { emb: DocumentChunk['embedding'] }) {
  return (
    <div className="space-y-3">
      <div className="flex flex-wrap gap-4 text-sm">
        <span><span className="text-muted-foreground">Dims:</span> <span className="font-mono">{emb.dims}</span></span>
        <span><span className="text-muted-foreground">Norma L2:</span> <span className="font-mono">{emb.norm}</span></span>
        <span><span className="text-muted-foreground">Máx:</span> <span className="font-mono">{emb.max}</span></span>
        <span><span className="text-muted-foreground">Mín:</span> <span className="font-mono">{emb.min}</span></span>
        <span><span className="text-muted-foreground">Sparsidad:</span> <span className="font-mono">{(emb.sparsity * 100).toFixed(1)}%</span></span>
      </div>
      <div>
        <p className="text-xs text-muted-foreground mb-1">Primeros 8 valores del vector:</p>
        <div className="flex flex-wrap gap-1">
          {emb.sample.map((v, i) => (
            <span
              key={i}
              className="rounded bg-muted px-1.5 py-0.5 font-mono text-xs tabular-nums"
            >
              {v >= 0 ? '+' : ''}{v.toFixed(5)}
            </span>
          ))}
          <span className="self-center text-xs text-muted-foreground">… +{emb.dims - 8} más</span>
        </div>
      </div>
    </div>
  )
}

// ─── Expanded chunk row ───────────────────────────────────────────────────

function ExpandedContent({
  content,
  embedding,
  colSpan,
}: {
  content: string
  embedding: DocumentChunk['embedding']
  colSpan: number
}) {
  return (
    <TableRow className="bg-muted/30 hover:bg-muted/30">
      <TableCell colSpan={colSpan} className="p-4">
        <div className="space-y-4">
          <div>
            <p className="mb-1 text-xs font-medium text-muted-foreground uppercase tracking-wide">Contenido completo</p>
            <div className="max-h-48 overflow-y-auto rounded border bg-white p-3 text-sm leading-relaxed whitespace-pre-wrap">
              {content}
            </div>
          </div>
          <Separator />
          <div>
            <p className="mb-2 text-xs font-medium text-muted-foreground uppercase tracking-wide">Embedding</p>
            <EmbeddingDetail emb={embedding} />
          </div>
        </div>
      </TableCell>
    </TableRow>
  )
}

// ─── Main page ────────────────────────────────────────────────────────────

export default function AdminChunksPage() {
  const currentUser = getUser()

  const [documents, setDocuments]         = useState<Document[]>([])
  const [selectedId, setSelectedId]       = useState<string>('')
  const [chunks, setChunks]               = useState<DocumentChunk[]>([])
  const [searchResults, setSearchResults] = useState<ChunkSearchResult[] | null>(null)
  const [query, setQuery]                 = useState('')
  const [searchInDoc, setSearchInDoc]     = useState(false)
  const [expandedId, setExpandedId]       = useState<number | null>(null)
  const [loadingChunks, setLoadingChunks] = useState(false)
  const [loadingSearch, setLoadingSearch] = useState(false)
  const [error, setError]                 = useState('')

  // Load READY documents on mount
  useEffect(() => {
    documentsApi.list().then((docs) => {
      const ready = docs.filter((d) => d.status === 'READY')
      setDocuments(ready)
      if (ready.length > 0) setSelectedId(ready[0].id)
    }).catch(() => setError('No se pudieron cargar los documentos'))
  }, [])

  // Load chunks when selected document changes
  const loadChunks = useCallback(async (docId: string) => {
    if (!docId) return
    setLoadingChunks(true)
    setSearchResults(null)
    setExpandedId(null)
    setError('')
    try {
      setChunks(await chunksApi.list(docId))
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Error al cargar chunks')
    } finally {
      setLoadingChunks(false)
    }
  }, [])

  useEffect(() => { loadChunks(selectedId) }, [selectedId, loadChunks])

  async function handleSearch() {
    const q = query.trim()
    if (!q) return
    setLoadingSearch(true)
    setError('')
    setExpandedId(null)
    try {
      const results = await chunksApi.search(q, searchInDoc ? selectedId : undefined, 10)
      setSearchResults(results)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Error en la búsqueda')
    } finally {
      setLoadingSearch(false)
    }
  }

  function clearSearch() {
    setQuery('')
    setSearchResults(null)
    setExpandedId(null)
  }

  function toggleExpand(id: number) {
    setExpandedId(prev => prev === id ? null : id)
  }

  // ── Admin guard ──
  if (currentUser?.role !== 'admin') {
    return (
      <div className="flex flex-col items-center justify-center h-64 gap-3 text-muted-foreground">
        <ShieldAlert className="size-10 opacity-40" />
        <p>Solo los administradores pueden acceder a esta sección.</p>
      </div>
    )
  }

  const selectedDoc = documents.find((d) => d.id === selectedId)
  const isSearchMode = searchResults !== null

  // ── Render ──
  return (
    <div className="space-y-4">

      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-xl font-semibold flex items-center gap-2">
            <ScanSearch className="size-5" />
            Inspector RAG
          </h1>
          <p className="text-sm text-muted-foreground mt-0.5">
            Visualizá los chunks generados por cada PDF y probá la búsqueda semántica del agente.
          </p>
        </div>
        {selectedDoc && (
          <div className="text-right text-sm text-muted-foreground">
            <p><span className="font-medium">{chunks.length}</span> chunks</p>
            <p>384 dims · all-MiniLM-L6-v2</p>
          </div>
        )}
      </div>

      {/* Document selector */}
      <Card className="p-3 flex items-center gap-3">
        <FileText className="size-4 text-muted-foreground shrink-0" />
        <div className="flex-1">
          <Select value={selectedId} onValueChange={(v) => { if (v) setSelectedId(v) }}>
            <SelectTrigger className="w-full">
              <SelectValue placeholder="Seleccioná un documento..." />
            </SelectTrigger>
            <SelectContent>
              {documents.map((d) => (
                <SelectItem key={d.id} value={d.id}>
                  {d.name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
        {documents.length === 0 && (
          <p className="text-sm text-muted-foreground">No hay documentos procesados.</p>
        )}
      </Card>

      {/* Search bar */}
      <div className="space-y-2">
        <div className="flex gap-2">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 size-4 text-muted-foreground" />
            <Input
              className="pl-9 pr-4"
              placeholder="Escribí una pregunta para ver qué chunks encuentra el RAG..."
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
            />
          </div>
          <Button onClick={handleSearch} disabled={loadingSearch || !query.trim()}>
            {loadingSearch ? 'Buscando...' : 'Buscar'}
          </Button>
          {isSearchMode && (
            <Button variant="ghost" onClick={clearSearch}>
              <X className="size-4" />
              Limpiar
            </Button>
          )}
        </div>
        <label className="flex items-center gap-2 text-sm text-muted-foreground cursor-pointer w-fit">
          <input
            type="checkbox"
            checked={searchInDoc}
            onChange={(e) => setSearchInDoc(e.target.checked)}
            className="rounded"
          />
          Buscar solo en el documento seleccionado
        </label>
      </div>

      {error && (
        <p className="text-sm text-destructive">{error}</p>
      )}

      {/* Results */}
      {isSearchMode ? (
        /* ── Search results table ── */
        <div className="space-y-2">
          <p className="text-sm text-muted-foreground flex items-center gap-1">
            <Layers className="size-4" />
            {searchResults!.length} resultados para <span className="font-medium italic">"{query}"</span>
          </p>
          <Card className="p-0 overflow-hidden">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead className="w-8" />
                  <TableHead>Documento</TableHead>
                  <TableHead className="w-14 text-center">Chunk</TableHead>
                  <TableHead className="w-24 text-center">Similitud</TableHead>
                  <TableHead className="w-20 text-right">Chars</TableHead>
                  <TableHead className="w-20 text-right">~Tokens</TableHead>
                  <TableHead>Vista previa</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {searchResults!.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={7} className="py-10 text-center text-muted-foreground">
                      Sin resultados
                    </TableCell>
                  </TableRow>
                ) : (
                  searchResults!.map((r) => (
                    <>
                      <TableRow
                        key={r.id}
                        className="cursor-pointer"
                        onClick={() => toggleExpand(r.id)}
                      >
                        <TableCell>
                          {expandedId === r.id
                            ? <ChevronDown className="size-4 text-muted-foreground" />
                            : <ChevronRight className="size-4 text-muted-foreground" />}
                        </TableCell>
                        <TableCell className="max-w-[200px] truncate text-sm" title={r.document_name}>
                          {r.document_name}
                        </TableCell>
                        <TableCell className="text-center font-mono text-sm">
                          #{r.chunk_index}
                        </TableCell>
                        <TableCell className="text-center">
                          <SimilarityBadge score={r.similarity} />
                        </TableCell>
                        <TableCell className="text-right font-mono text-sm tabular-nums">
                          {r.char_count.toLocaleString('es-AR')}
                        </TableCell>
                        <TableCell className="text-right font-mono text-sm tabular-nums">
                          ~{r.estimated_tokens.toLocaleString('es-AR')}
                        </TableCell>
                        <TableCell className="text-sm text-muted-foreground max-w-xs">
                          <span className="line-clamp-2">{r.content}</span>
                        </TableCell>
                      </TableRow>
                      {expandedId === r.id && (
                        <ExpandedContent
                          content={r.content}
                          embedding={r.embedding}
                          colSpan={7}
                        />
                      )}
                    </>
                  ))
                )}
              </TableBody>
            </Table>
          </Card>
        </div>
      ) : (
        /* ── Chunk list table ── */
        <Card className="p-0 overflow-hidden">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="w-8" />
                <TableHead className="w-14 text-center">Chunk</TableHead>
                <TableHead className="w-20 text-right">Chars</TableHead>
                <TableHead className="w-20 text-right">~Tokens</TableHead>
                <TableHead className="w-24 text-center">Norma L2</TableHead>
                <TableHead>Vista previa</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {loadingChunks ? (
                <TableRow>
                  <TableCell colSpan={6} className="py-10 text-center text-muted-foreground">
                    Cargando chunks...
                  </TableCell>
                </TableRow>
              ) : chunks.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={6} className="py-10 text-center text-muted-foreground">
                    {selectedDoc
                      ? 'Este documento no tiene chunks procesados.'
                      : 'Seleccioná un documento para ver sus chunks.'}
                  </TableCell>
                </TableRow>
              ) : (
                chunks.map((c) => (
                  <>
                    <TableRow
                      key={c.id}
                      className="cursor-pointer"
                      onClick={() => toggleExpand(c.id)}
                    >
                      <TableCell>
                        {expandedId === c.id
                          ? <ChevronDown className="size-4 text-muted-foreground" />
                          : <ChevronRight className="size-4 text-muted-foreground" />}
                      </TableCell>
                      <TableCell className="text-center font-mono text-sm">
                        #{c.chunk_index}
                      </TableCell>
                      <TableCell className="text-right font-mono text-sm tabular-nums">
                        {c.char_count.toLocaleString('es-AR')}
                      </TableCell>
                      <TableCell className="text-right font-mono text-sm tabular-nums">
                        ~{c.estimated_tokens.toLocaleString('es-AR')}
                      </TableCell>
                      <TableCell className="text-center font-mono text-sm tabular-nums">
                        {c.embedding.norm}
                      </TableCell>
                      <TableCell className="text-sm text-muted-foreground max-w-xs">
                        <span className="line-clamp-2">{c.content}</span>
                      </TableCell>
                    </TableRow>
                    {expandedId === c.id && (
                      <ExpandedContent
                        content={c.content}
                        embedding={c.embedding}
                        colSpan={6}
                      />
                    )}
                  </>
                ))
              )}
            </TableBody>
          </Table>
        </Card>
      )}
    </div>
  )
}

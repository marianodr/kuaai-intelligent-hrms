'use client'

import { useEffect, useState, useRef, useCallback } from 'react'
import { agentApi, threadsApi } from '@/lib/api'
import { getUser } from '@/lib/auth'
import type { ChatMessage, ConversationThread } from '@/types'
import { Button } from '@/components/ui/button'
import { Textarea } from '@/components/ui/textarea'
import { Send, Bot, User, Plus, Trash2, MessageSquare } from 'lucide-react'
import { cn } from '@/lib/utils'

export default function ChatPage() {
  const user = getUser()
  const [threads, setThreads]           = useState<ConversationThread[]>([])
  const [activeThread, setActiveThread] = useState<ConversationThread | null>(null)
  const [messages, setMessages]         = useState<ChatMessage[]>([])
  const [input, setInput]               = useState('')
  const [loading, setLoading]           = useState(false)
  const [loadingHistory, setLoadingHistory] = useState(false)
  const bottomRef = useRef<HTMLDivElement>(null)

  const fetchThreads = useCallback(async () => {
    if (!user) return
    const list = await threadsApi.list(user.id)
    setThreads(list)
    return list
  }, [user])

  useEffect(() => {
    if (!user) return
    fetchThreads().then((list) => {
      if (list && list.length > 0) {
        selectThread(list[0])
      }
    })
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  async function selectThread(thread: ConversationThread) {
    setActiveThread(thread)
    setMessages([])
    if (!user) return
    setLoadingHistory(true)
    try {
      const msgs = await agentApi.history(user.id, thread.id)
      setMessages(msgs)
    } finally {
      setLoadingHistory(false)
    }
  }

  async function createNewThread() {
    if (!user) return
    const thread = await threadsApi.create(user.id)
    const list = await fetchThreads()
    const created = list?.find((t) => t.id === thread.id) ?? thread
    setActiveThread(created)
    setMessages([])
  }

  async function deleteThread(thread: ConversationThread) {
    if (!confirm(`¿Eliminar "${thread.name}"?`)) return
    await threadsApi.delete(thread.id)
    const list = await fetchThreads()
    if (activeThread?.id === thread.id) {
      if (list && list.length > 0) {
        selectThread(list[0])
      } else {
        setActiveThread(null)
        setMessages([])
      }
    }
  }

  async function handleSend() {
    const question = input.trim()
    if (!question || loading || !user || !activeThread) return

    const userMsg: ChatMessage = { role: 'user', content: question }
    setMessages((prev) => [...prev, userMsg])
    setInput('')
    setLoading(true)

    try {
      const { answer } = await agentApi.chat(question, user.id, activeThread.id)
      const assistantMsg: ChatMessage = { role: 'assistant', content: answer }
      setMessages((prev) => [...prev, assistantMsg])
      setThreads((prev) =>
        prev.map((t) =>
          t.id === activeThread.id
            ? { ...t, last_message_at: new Date().toISOString() }
            : t,
        ),
      )
    } catch (err: unknown) {
      const errMsg: ChatMessage = {
        role: 'assistant',
        content: `Error: ${err instanceof Error ? err.message : 'No se pudo obtener respuesta'}`,
      }
      setMessages((prev) => [...prev, errMsg])
    } finally {
      setLoading(false)
    }
  }

  function handleKeyDown(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  return (
    <div className="flex h-full max-h-[calc(100vh-8rem)] gap-3">
      {/* ── Thread list ─────────────────────────────── */}
      <div className="w-52 shrink-0 flex flex-col border rounded-xl bg-white overflow-hidden">
        <div className="flex items-center justify-between px-3 py-2 border-b">
          <span className="text-xs font-semibold text-muted-foreground uppercase tracking-wide">Conversaciones</span>
          <Button variant="ghost" size="icon" className="size-7" onClick={createNewThread} title="Nueva conversación">
            <Plus className="size-4" />
          </Button>
        </div>
        <div className="flex-1 overflow-y-auto">
          {threads.length === 0 && (
            <p className="text-xs text-muted-foreground text-center py-6 px-3">
              No hay conversaciones.
            </p>
          )}
          {threads.map((t) => (
            <div
              key={t.id}
              className={cn(
                'group flex items-center justify-between gap-1 px-3 py-2 cursor-pointer text-sm transition-colors',
                activeThread?.id === t.id
                  ? 'bg-primary-light text-primary'
                  : 'hover:bg-surface text-muted-foreground hover:text-foreground',
              )}
              onClick={() => selectThread(t)}
            >
              <div className="flex items-center gap-2 min-w-0">
                <MessageSquare className="size-3.5 shrink-0" />
                <span className="truncate text-xs">{t.name}</span>
              </div>
              <Button
                variant="ghost"
                size="icon"
                className="size-5 shrink-0 opacity-0 group-hover:opacity-100"
                onClick={(e) => { e.stopPropagation(); deleteThread(t) }}
              >
                <Trash2 className="size-3 text-destructive" />
              </Button>
            </div>
          ))}
        </div>
      </div>

      {/* ── Chat area ───────────────────────────────── */}
      <div className="flex flex-col flex-1 min-w-0">
        <h1 className="text-xl font-semibold mb-4 shrink-0">
          {activeThread?.name ?? 'Asistente IA'}
        </h1>

        <div className="flex-1 overflow-y-auto space-y-4 pr-1 mb-4">
          {!activeThread && (
            <div className="flex flex-col items-center justify-center h-48 text-center text-muted-foreground space-y-2">
              <Bot className="size-10 opacity-40" />
              <p className="text-sm">Creá una nueva conversación para comenzar.</p>
              <Button variant="outline" size="sm" onClick={createNewThread}>
                <Plus className="size-4 mr-1" />
                Nueva conversación
              </Button>
            </div>
          )}

          {loadingHistory && (
            <div className="text-center text-sm text-muted-foreground py-8">Cargando historial...</div>
          )}

          {messages.length === 0 && activeThread && !loadingHistory && (
            <div className="flex flex-col items-center justify-center h-48 text-center text-muted-foreground space-y-2">
              <Bot className="size-10 opacity-40" />
              <p className="text-sm">
                Preguntá sobre asistencia, empleados, documentos de la empresa o tardanzas.
              </p>
            </div>
          )}

          {messages.map((msg, i) => (
            <div
              key={i}
              className={cn(
                'flex gap-3 text-sm',
                msg.role === 'user' ? 'flex-row-reverse' : 'flex-row',
              )}
            >
              <div className={cn(
                'flex size-7 shrink-0 items-center justify-center rounded-full',
                msg.role === 'user' ? 'bg-primary text-primary-foreground' : 'bg-muted',
              )}>
                {msg.role === 'user' ? <User className="size-4" /> : <Bot className="size-4" />}
              </div>
              <div className={cn(
                'max-w-[75%] rounded-xl px-3 py-2 leading-relaxed whitespace-pre-wrap',
                msg.role === 'user'
                  ? 'bg-primary text-primary-foreground rounded-tr-none'
                  : 'bg-muted rounded-tl-none',
              )}>
                {msg.content}
              </div>
            </div>
          ))}

          {loading && (
            <div className="flex gap-3 text-sm">
              <div className="flex size-7 items-center justify-center rounded-full bg-muted">
                <Bot className="size-4" />
              </div>
              <div className="bg-muted rounded-xl rounded-tl-none px-3 py-2">
                <span className="animate-pulse">Pensando...</span>
              </div>
            </div>
          )}
          <div ref={bottomRef} />
        </div>

        <div className="shrink-0 flex gap-2 items-end">
          <Textarea
            placeholder={
              activeThread
                ? 'Escribí tu pregunta... (Enter para enviar, Shift+Enter para nueva línea)'
                : 'Creá una conversación para comenzar...'
            }
            className="resize-none min-h-[2.5rem] max-h-32"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            disabled={!activeThread}
            rows={1}
          />
          <Button
            size="icon"
            onClick={handleSend}
            disabled={loading || !input.trim() || !activeThread}
          >
            <Send />
          </Button>
        </div>
      </div>
    </div>
  )
}

'use client'

import { useEffect, useState, useRef } from 'react'
import { agentApi } from '@/lib/api'
import { getUser } from '@/lib/auth'
import type { ChatMessage } from '@/types'
import { Button } from '@/components/ui/button'
import { Textarea } from '@/components/ui/textarea'
import { Send, Bot, User } from 'lucide-react'
import { cn } from '@/lib/utils'

export default function ChatPage() {
  const user = getUser()
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [threadId] = useState(() => `user-${user?.id ?? 'anon'}`)
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!user) return
    agentApi.history(user.id).then((msgs) => {
      if (msgs.length > 0) setMessages(msgs)
    })
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  async function handleSend() {
    const question = input.trim()
    if (!question || loading || !user) return

    const userMsg: ChatMessage = { role: 'user', content: question }
    setMessages((prev) => [...prev, userMsg])
    setInput('')
    setLoading(true)

    try {
      const { answer } = await agentApi.chat(question, user.id, threadId)
      const assistantMsg: ChatMessage = { role: 'assistant', content: answer }
      setMessages((prev) => [...prev, assistantMsg])
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
    <div className="flex flex-col h-full max-h-[calc(100vh-8rem)]">
      <h1 className="text-xl font-semibold mb-4 shrink-0">Asistente IA</h1>

      <div className="flex-1 overflow-y-auto space-y-4 pr-1 mb-4">
        {messages.length === 0 && (
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
          placeholder="Escribí tu pregunta... (Enter para enviar, Shift+Enter para nueva línea)"
          className="resize-none min-h-[2.5rem] max-h-32"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          rows={1}
        />
        <Button size="icon" onClick={handleSend} disabled={loading || !input.trim()}>
          <Send />
        </Button>
      </div>
    </div>
  )
}

-- Sprint 2: múltiples hilos de conversación + TTL 30 días

CREATE TABLE IF NOT EXISTS conversation_threads (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id         INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  name            VARCHAR(255) NOT NULL DEFAULT 'Nueva conversación',
  created_at      TIMESTAMP DEFAULT NOW(),
  last_message_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_threads_user_id ON conversation_threads(user_id);
CREATE INDEX IF NOT EXISTS idx_threads_last_message ON conversation_threads(last_message_at);

ALTER TABLE chat_history
  ADD COLUMN IF NOT EXISTS thread_id UUID REFERENCES conversation_threads(id) ON DELETE SET NULL;

CREATE INDEX IF NOT EXISTS idx_chat_history_thread_id ON chat_history(thread_id);

-- Sprint 3: tabla de logs del sistema para auditoría

CREATE TABLE IF NOT EXISTS system_logs (
  id         BIGSERIAL PRIMARY KEY,
  level      VARCHAR(10)  NOT NULL CHECK (level IN ('INFO', 'WARN', 'ERROR')),
  service    VARCHAR(20)  NOT NULL CHECK (service IN ('nest', 'fastapi')),
  event      VARCHAR(100) NOT NULL,
  user_id    INTEGER REFERENCES users(id) ON DELETE SET NULL,
  detail     JSONB,
  created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_system_logs_created_at ON system_logs(created_at);
CREATE INDEX IF NOT EXISTS idx_system_logs_level ON system_logs(level);
CREATE INDEX IF NOT EXISTS idx_system_logs_event ON system_logs(event);

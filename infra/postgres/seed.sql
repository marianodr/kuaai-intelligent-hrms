-- =============================================================
-- Kuaai HRMS — Datos de prueba
-- Ejecutar después de init.sql (solo en desarrollo/demo)
-- =============================================================

-- Usuarios del sistema
-- Contraseñas: admin123 / rrhh123 (bcrypt rounds=10)
INSERT INTO users (email, password, role) VALUES
  ('admin@kuaai.com',  '$2b$10$ah1gJllmMZZ1fTC/GZBM/uVX9pdQEwcqVSSFAg6vqYkTzV9c4QGZC', 'admin'),
  ('rrhh@kuaai.com',   '$2b$10$jufUOx.pH1BPts1h/IEVbeFwEZqLQikw6C.LipO6wnSrM.J..tg/G', 'rrhh')
ON CONFLICT (email) DO NOTHING;

-- Empleados (rfid_code = UID decimal que devuelve el RC522)
INSERT INTO employees (first_name, last_name, email, legajo, rfid_code, department) VALUES
  ('Juan',      'García',     'juan.garcia@empresa.com',     'EMP-001', '37194205',  'Administración'),
  ('María',     'López',      'maria.lopez@empresa.com',     'EMP-002', '346298099', 'Administración'),
  ('Pedro',     'Ramírez',    'pedro.ramirez@empresa.com',   'EMP-003', '112233445', 'Operaciones'),
  ('Ana',       'Fernández',  'ana.fernandez@empresa.com',   'EMP-004', '556677889', 'Operaciones'),
  ('Carlos',    'Martínez',   'carlos.martinez@empresa.com', 'EMP-005', '998877665', 'Operaciones'),
  ('Laura',     'Giménez',    'laura.gimenez@empresa.com',   'EMP-006', '443322110', 'Ventas'),
  ('Roberto',   'Torres',     'roberto.torres@empresa.com',  'EMP-007', '667788990', 'Ventas'),
  ('Sofía',     'Benítez',    'sofia.benitez@empresa.com',   'EMP-008', '221100334', 'Ventas')
ON CONFLICT (legajo) DO NOTHING;

-- =============================================================
-- Registros de asistencia — 2026-03-02 hasta CURRENT_DATE
-- Generado dinámicamente con generate_series (lunes a viernes)
-- Lógica:
--   · 88 % de asistencia  (h % 100 >= 12)
--   · 12 % de tardanzas   ((h/100) % 100 < 12)
--   · Entrada puntual: 07:45 – 08:15  |  Entrada tarde: 08:16 – 08:44
--   · SALIDA solo para días anteriores a hoy (auto-generada por cron el día actual)
-- =============================================================
TRUNCATE attendance_records RESTART IDENTITY;

WITH
  working_days AS (
    SELECT d::date AS day
    FROM generate_series('2026-03-02'::date, CURRENT_DATE, '1 day') d
    WHERE EXTRACT(DOW FROM d) BETWEEN 1 AND 5
  ),
  slots AS (
    SELECT
      e.id                                                          AS employee_id,
      w.day,
      abs(hashtext(e.id::text || w.day::text)::bigint)             AS h
    FROM employees e CROSS JOIN working_days w
    WHERE e.status = 'ACTIVO'
  ),
  present_slots AS (
    SELECT
      employee_id,
      day,
      (h / 100) % 100 < 12                                        AS is_late,
      CASE WHEN (h / 100) % 100 < 12
        THEN day + ((8 * 60 + 16 + (h / 10000) % 29) || ' minutes')::interval
        ELSE day + ((7 * 60 + 45 + (h / 10000) % 31) || ' minutes')::interval
      END                                                           AS entry_ts
    FROM slots
    WHERE h % 100 >= 12
  )
INSERT INTO attendance_records (employee_id, timestamp, record_type, is_late, auto_generated)
SELECT employee_id, entry_ts,                           'ENTRADA', is_late, false FROM present_slots
UNION ALL
SELECT employee_id, (day + INTERVAL '16 hours')::timestamp, 'SALIDA',  false,   false
FROM present_slots
WHERE day < CURRENT_DATE;

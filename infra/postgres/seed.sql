-- =============================================================
-- Kuaai HRMS — Datos de prueba
-- Ejecutar después de init.sql (solo en desarrollo/demo)
-- =============================================================

-- Usuarios del sistema — admin y rrhh se crean automáticamente al startup
-- utilizando ADMIN_EMAIL, ADMIN_PASSWORD y RRHH_EMAIL, RRHH_PASSWORD del .env

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
--
-- · Meses anteriores al actual: 100% determinístico vía
--   hashtext(employee_id || día) — mismos datos en cada corrida,
--   para no romper demos/evaluaciones que dependan de historial fijo.
--     - 88 % de asistencia  (h % 100 >= 12)
--     - 12 % de tardanzas   ((h/100) % 100 < 12)
--
-- · Mes actual: configurable vía parámetros psql (random() real,
--   cambia en cada corrida salvo que fijes los mismos parámetros):
--     -v attendance_pct=NN          (default 88) % de presentismo
--     -v late_count_last_day=N      (default 0)  tardanzas forzadas
--                                   en el último día hábil disponible
--
-- Entrada puntual: 07:45–08:15 | Entrada tarde: 08:16–08:44
-- SALIDA solo para días anteriores a hoy (auto-generada por cron el día actual)
-- =============================================================
TRUNCATE attendance_records RESTART IDENTITY;

\if :{?attendance_pct}
\else
  \set attendance_pct 88
\endif
\if :{?late_count_last_day}
\else
  \set late_count_last_day 0
\endif

WITH
  working_days AS (
    SELECT d::date AS day
    FROM generate_series('2026-03-02'::date, CURRENT_DATE, '1 day') d
    WHERE EXTRACT(DOW FROM d) BETWEEN 1 AND 5
  ),
  last_day AS (
    SELECT MAX(day) AS day FROM working_days
  ),

  -- ── Meses anteriores al actual: hash determinístico (sin cambios) ──
  historical_slots AS (
    SELECT
      e.id                                              AS employee_id,
      w.day,
      abs(hashtext(e.id::text || w.day::text)::bigint)  AS h
    FROM employees e CROSS JOIN working_days w
    WHERE e.status = 'ACTIVO'
      AND w.day < date_trunc('month', CURRENT_DATE)::date
  ),
  historical_present AS (
    SELECT
      employee_id,
      day,
      (h / 100) % 100 < 12                                        AS is_late,
      CASE WHEN (h / 100) % 100 < 12
        THEN day + ((8 * 60 + 16 + (h / 10000) % 29) || ' minutes')::interval
        ELSE day + ((7 * 60 + 45 + (h / 10000) % 31) || ' minutes')::interval
      END                                                           AS entry_ts
    FROM historical_slots
    WHERE h % 100 >= 12
  ),

  -- ── Mes actual: parametrizado, random() real en cada corrida ──
  current_days AS (
    SELECT day FROM working_days
    WHERE day >= date_trunc('month', CURRENT_DATE)::date
  ),
  current_present_raw AS (
    SELECT e.id AS employee_id, cd.day
    FROM employees e CROSS JOIN current_days cd
    WHERE e.status = 'ACTIVO'
      AND (random() * 100) < :attendance_pct
  ),
  current_present AS (
    SELECT
      cpr.employee_id,
      cpr.day,
      CASE
        WHEN cpr.day = (SELECT day FROM last_day) THEN
          row_number() OVER (PARTITION BY cpr.day ORDER BY random()) <= :late_count_last_day
        ELSE random() < 0.12
      END AS is_late
    FROM current_present_raw cpr
  ),
  current_entries AS (
    SELECT
      employee_id,
      day,
      is_late,
      CASE WHEN is_late
        THEN day + ((8 * 60 + 16 + floor(random() * 29)) || ' minutes')::interval
        ELSE day + ((7 * 60 + 45 + floor(random() * 31)) || ' minutes')::interval
      END AS entry_ts
    FROM current_present
  ),

  all_present AS (
    SELECT employee_id, day, is_late, entry_ts FROM historical_present
    UNION ALL
    SELECT employee_id, day, is_late, entry_ts FROM current_entries
  )
INSERT INTO attendance_records (employee_id, timestamp, record_type, is_late, auto_generated)
SELECT employee_id, entry_ts,                              'ENTRADA', is_late, false FROM all_present
UNION ALL
SELECT employee_id, (day + INTERVAL '16 hours')::timestamp, 'SALIDA',  false,   false
FROM all_present
WHERE day < CURRENT_DATE;

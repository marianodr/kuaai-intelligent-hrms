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
-- Registros de asistencia — Mayo 2026
-- Semana 1: lun 05 al vie 09
-- Semana 2: lun 12 al vie 16 (parcial, solo hasta el 12)
-- =============================================================

-- Lunes 2026-05-04
INSERT INTO attendance_records (employee_id, timestamp, record_type, is_late) VALUES
  (1, '2026-05-04 07:58:00', 'ENTRADA', false),
  (2, '2026-05-04 08:02:00', 'ENTRADA', false),
  (3, '2026-05-04 08:25:00', 'ENTRADA', true),   -- tarde
  (4, '2026-05-04 08:01:00', 'ENTRADA', false),
  (5, '2026-05-04 07:55:00', 'ENTRADA', false),
  (6, '2026-05-04 08:10:00', 'ENTRADA', false),
  (7, '2026-05-04 08:30:00', 'ENTRADA', true),   -- tarde
  (8, '2026-05-04 08:00:00', 'ENTRADA', false),
  (1, '2026-05-04 16:00:00', 'SALIDA',  false),
  (2, '2026-05-04 16:00:00', 'SALIDA',  false),
  (3, '2026-05-04 16:00:00', 'SALIDA',  false),
  (4, '2026-05-04 16:00:00', 'SALIDA',  false),
  (5, '2026-05-04 16:00:00', 'SALIDA',  false),
  (6, '2026-05-04 16:00:00', 'SALIDA',  false),
  (7, '2026-05-04 16:00:00', 'SALIDA',  false),
  (8, '2026-05-04 16:00:00', 'SALIDA',  false);

-- Martes 2026-05-06 (empleado 5 ausente)
INSERT INTO attendance_records (employee_id, timestamp, record_type, is_late) VALUES
  (1, '2026-05-06 07:59:00', 'ENTRADA', false),
  (2, '2026-05-06 08:20:00', 'ENTRADA', true),   -- tarde
  (3, '2026-05-06 08:05:00', 'ENTRADA', false),
  (4, '2026-05-06 08:00:00', 'ENTRADA', false),
  (6, '2026-05-06 08:01:00', 'ENTRADA', false),
  (7, '2026-05-06 08:45:00', 'ENTRADA', true),   -- tarde
  (8, '2026-05-06 08:00:00', 'ENTRADA', false),
  (1, '2026-05-06 16:00:00', 'SALIDA',  false),
  (2, '2026-05-06 16:00:00', 'SALIDA',  false),
  (3, '2026-05-06 16:00:00', 'SALIDA',  false),
  (4, '2026-05-06 16:00:00', 'SALIDA',  false),
  (6, '2026-05-06 16:00:00', 'SALIDA',  false),
  (7, '2026-05-06 16:00:00', 'SALIDA',  false),
  (8, '2026-05-06 16:00:00', 'SALIDA',  false);

-- Miércoles 2026-05-07 (todos presentes)
INSERT INTO attendance_records (employee_id, timestamp, record_type, is_late) VALUES
  (1, '2026-05-07 08:00:00', 'ENTRADA', false),
  (2, '2026-05-07 08:03:00', 'ENTRADA', false),
  (3, '2026-05-07 08:10:00', 'ENTRADA', false),
  (4, '2026-05-07 07:58:00', 'ENTRADA', false),
  (5, '2026-05-07 08:00:00', 'ENTRADA', false),
  (6, '2026-05-07 08:00:00', 'ENTRADA', false),
  (7, '2026-05-07 08:16:00', 'ENTRADA', true),   -- 1 min de diferencia
  (8, '2026-05-07 08:02:00', 'ENTRADA', false),
  (1, '2026-05-07 16:00:00', 'SALIDA',  false),
  (2, '2026-05-07 16:00:00', 'SALIDA',  false),
  (3, '2026-05-07 16:00:00', 'SALIDA',  false),
  (4, '2026-05-07 16:00:00', 'SALIDA',  false),
  (5, '2026-05-07 16:00:00', 'SALIDA',  false),
  (6, '2026-05-07 16:00:00', 'SALIDA',  false),
  (7, '2026-05-07 16:00:00', 'SALIDA',  false),
  (8, '2026-05-07 16:00:00', 'SALIDA',  false);

-- Jueves 2026-05-08 (emp 3 y 7 ausentes)
INSERT INTO attendance_records (employee_id, timestamp, record_type, is_late) VALUES
  (1, '2026-05-08 07:57:00', 'ENTRADA', false),
  (2, '2026-05-08 08:00:00', 'ENTRADA', false),
  (4, '2026-05-08 08:00:00', 'ENTRADA', false),
  (5, '2026-05-08 08:19:00', 'ENTRADA', true),   -- tarde
  (6, '2026-05-08 08:01:00', 'ENTRADA', false),
  (8, '2026-05-08 08:00:00', 'ENTRADA', false),
  (1, '2026-05-08 16:00:00', 'SALIDA',  false),
  (2, '2026-05-08 16:00:00', 'SALIDA',  false),
  (4, '2026-05-08 16:00:00', 'SALIDA',  false),
  (5, '2026-05-08 16:00:00', 'SALIDA',  false),
  (6, '2026-05-08 16:00:00', 'SALIDA',  false),
  (8, '2026-05-08 16:00:00', 'SALIDA',  false);

-- Viernes 2026-05-09 (todos presentes)
INSERT INTO attendance_records (employee_id, timestamp, record_type, is_late) VALUES
  (1, '2026-05-09 08:00:00', 'ENTRADA', false),
  (2, '2026-05-09 08:05:00', 'ENTRADA', false),
  (3, '2026-05-09 08:00:00', 'ENTRADA', false),
  (4, '2026-05-09 08:00:00', 'ENTRADA', false),
  (5, '2026-05-09 08:31:00', 'ENTRADA', true),   -- tarde
  (6, '2026-05-09 08:00:00', 'ENTRADA', false),
  (7, '2026-05-09 08:00:00', 'ENTRADA', false),
  (8, '2026-05-09 08:03:00', 'ENTRADA', false),
  (1, '2026-05-09 16:00:00', 'SALIDA',  false),
  (2, '2026-05-09 16:00:00', 'SALIDA',  false),
  (3, '2026-05-09 16:00:00', 'SALIDA',  false),
  (4, '2026-05-09 16:00:00', 'SALIDA',  false),
  (5, '2026-05-09 16:00:00', 'SALIDA',  false),
  (6, '2026-05-09 16:00:00', 'SALIDA',  false),
  (7, '2026-05-09 16:00:00', 'SALIDA',  false),
  (8, '2026-05-09 16:00:00', 'SALIDA',  false);

-- Lunes 2026-05-12 (emp 4 y 6 ausentes)
INSERT INTO attendance_records (employee_id, timestamp, record_type, is_late) VALUES
  (1, '2026-05-12 08:02:00', 'ENTRADA', false),
  (2, '2026-05-12 08:00:00', 'ENTRADA', false),
  (3, '2026-05-12 08:22:00', 'ENTRADA', true),   -- tarde
  (5, '2026-05-12 08:01:00', 'ENTRADA', false),
  (7, '2026-05-12 08:00:00', 'ENTRADA', false),
  (8, '2026-05-12 08:00:00', 'ENTRADA', false),
  (1, '2026-05-12 16:00:00', 'SALIDA',  false),
  (2, '2026-05-12 16:00:00', 'SALIDA',  false),
  (3, '2026-05-12 16:00:00', 'SALIDA',  false),
  (5, '2026-05-12 16:00:00', 'SALIDA',  false),
  (7, '2026-05-12 16:00:00', 'SALIDA',  false),
  (8, '2026-05-12 16:00:00', 'SALIDA',  false);

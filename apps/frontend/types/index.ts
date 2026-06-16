export type UserRole = 'admin' | 'rrhh'

export interface AuthUser {
  id: number
  email: string
  role: UserRole
}

export interface LoginResponse {
  access_token: string
  user: AuthUser
}

export type EmployeeStatus = 'ACTIVO' | 'INACTIVO'

export interface Employee {
  id: number
  first_name: string
  last_name: string
  email?: string
  legajo: string
  rfid_code: string
  department?: string
  status: EmployeeStatus
  created_at: string
  updated_at: string
}

export interface EmployeeListResponse {
  data: Employee[]
  total: number
  page: number
  limit: number
  totalPages: number
}

export interface CreateEmployeeDto {
  first_name: string
  last_name: string
  email?: string
  legajo: string
  rfid_code: string
  department?: string
}

export interface UpdateEmployeeDto extends Partial<CreateEmployeeDto> {
  status?: EmployeeStatus
}

export interface AbsentEmployee {
  id: number
  name: string
  department?: string
}

export interface TodayAttendance {
  date: string
  total_active: number
  present: number
  absent: number
  attendance_pct: number
  absent_employees: AbsentEmployee[]
}

export interface MonthlyAverage {
  month: number
  year: number
  workdays: number
  average_attendance_pct: number
}

export interface TardinessEntry {
  employee_id: number
  name: string
  department?: string
  count: number
}

export interface TardinessReport {
  month: number
  year: number
  tardiness: TardinessEntry[]
}

export type DocumentStatus = 'PROCESSING' | 'READY' | 'ERROR'

export interface Document {
  id: string
  name: string
  minio_path?: string
  status: DocumentStatus
  progress?: string | null
  created_at: string
}

export interface ChatMessage {
  role: 'user' | 'assistant'
  content: string
  created_at?: string
}

export interface ChatResponse {
  answer: string
  thread_id: string
}

export interface ConversationThread {
  id: string
  name: string
  created_at: string
  last_message_at: string
}

export interface HrUser {
  id: number
  email: string
  role: 'admin' | 'rrhh'
  is_active: boolean
  created_at: string
}

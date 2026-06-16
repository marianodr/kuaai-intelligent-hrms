import { getToken } from '@/lib/auth'
import type {
  LoginResponse, Employee, EmployeeListResponse,
  CreateEmployeeDto, UpdateEmployeeDto,
  TodayAttendance, MonthlyAverage, TardinessReport,
  Document, ChatMessage, ChatResponse,
  ConversationThread, HrUser,
} from '@/types'

const NEST = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:3001'

async function request<T>(url: string, init: RequestInit = {}): Promise<T> {
  const token = getToken()
  const res = await fetch(url, {
    ...init,
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...(init.headers ?? {}),
    },
  })
  if (!res.ok) {
    const body = await res.json().catch(() => ({}))
    throw new Error(body.message ?? body.detail ?? `Error ${res.status}`)
  }
  return res.json() as Promise<T>
}

// ─── Auth ──────────────────────────────────────────────────────────────────
export const authApi = {
  login: (email: string, password: string) =>
    request<LoginResponse>(`${NEST}/auth/login`, {
      method: 'POST',
      body: JSON.stringify({ email, password }),
    }),
}

// ─── Employees ─────────────────────────────────────────────────────────────
export const employeesApi = {
  list: (page = 1, limit = 10, name?: string, department?: string) => {
    const params = new URLSearchParams({ page: String(page), limit: String(limit) })
    if (name) params.set('name', name)
    if (department) params.set('department', department)
    return request<EmployeeListResponse>(`${NEST}/employees?${params}`)
  },
  get: (id: number) => request<Employee>(`${NEST}/employees/${id}`),
  create: (dto: CreateEmployeeDto) =>
    request<Employee>(`${NEST}/employees`, { method: 'POST', body: JSON.stringify(dto) }),
  update: (id: number, dto: UpdateEmployeeDto) =>
    request<Employee>(`${NEST}/employees/${id}`, { method: 'PUT', body: JSON.stringify(dto) }),
  deactivate: (id: number) =>
    request<Employee>(`${NEST}/employees/${id}`, { method: 'DELETE' }),
}

// ─── Dashboard ─────────────────────────────────────────────────────────────
export const dashboardApi = {
  today: () => request<TodayAttendance>(`${NEST}/dashboard/today`),
  monthlyAverage: (month: number, year: number) =>
    request<MonthlyAverage>(`${NEST}/dashboard/monthly-average?month=${month}&year=${year}`),
  tardiness: (month: number, year: number) =>
    request<TardinessReport>(`${NEST}/dashboard/tardiness?month=${month}&year=${year}`),
}

// ─── Documents ─────────────────────────────────────────────────────────────
export const documentsApi = {
  list: () => request<Document[]>(`${NEST}/documents`),
  process: (documentId: string) =>
    request<{ message: string }>(`${NEST}/documents/process`, {
      method: 'POST',
      body: JSON.stringify({ document_id: documentId }),
    }),
  delete: (id: string) =>
    request<{ message: string }>(`${NEST}/documents/${id}`, { method: 'DELETE' }),

  upload: async (file: File, userId: number): Promise<{ document_id: string }> => {
    const token = getToken()
    const form = new FormData()
    form.append('file', file)
    form.append('uploaded_by', String(userId))
    const res = await fetch(`${NEST}/documents/upload`, {
      method: 'POST',
      headers: token ? { Authorization: `Bearer ${token}` } : {},
      body: form,
    })
    if (!res.ok) throw new Error(`Upload error ${res.status}`)
    return res.json()
  },
}

// ─── Agent / Chat ──────────────────────────────────────────────────────────
export const agentApi = {
  chat: (question: string, userId: number, threadId: string) =>
    request<ChatResponse>(`${NEST}/agent/chat`, {
      method: 'POST',
      body: JSON.stringify({ question, user_id: userId, thread_id: threadId }),
    }),
  history: (userId: number, threadId?: string, limit = 50) => {
    const qs = threadId
      ? `${NEST}/agent/history/${userId}?limit=${limit}&thread_id=${threadId}`
      : `${NEST}/agent/history/${userId}?limit=${limit}`
    return request<ChatMessage[]>(qs)
  },
}

// ─── Conversation threads ──────────────────────────────────────────────────
export const threadsApi = {
  list: (userId: number) =>
    request<ConversationThread[]>(`${NEST}/threads/${userId}`),
  create: (userId: number, name = 'Nueva conversación') =>
    request<ConversationThread>(`${NEST}/threads`, {
      method: 'POST',
      body: JSON.stringify({ user_id: userId, name }),
    }),
  rename: (threadId: string, name: string) =>
    request<ConversationThread>(`${NEST}/threads/${threadId}/rename`, {
      method: 'PATCH',
      body: JSON.stringify({ name }),
    }),
  delete: (threadId: string) =>
    request<{ message: string }>(`${NEST}/threads/${threadId}`, { method: 'DELETE' }),
}

// ─── HR Users (admin) ──────────────────────────────────────────────────────
export const usersApi = {
  list: () => request<HrUser[]>(`${NEST}/users`),
  create: (email: string, password: string, role: 'admin' | 'rrhh') =>
    request<HrUser>(`${NEST}/users`, {
      method: 'POST',
      body: JSON.stringify({ email, password, role }),
    }),
  update: (id: number, dto: Partial<{ email: string; password: string; role: string; is_active: boolean }>) =>
    request<HrUser>(`${NEST}/users/${id}`, {
      method: 'PATCH',
      body: JSON.stringify(dto),
    }),
  deactivate: (id: number) =>
    request<HrUser>(`${NEST}/users/${id}/deactivate`, { method: 'PATCH' }),
}

// ─── Document download ─────────────────────────────────────────────────────
export function getDocumentDownloadUrl(documentId: string): string {
  const token = getToken()
  return `${NEST}/documents/${documentId}/download${token ? `?token=${encodeURIComponent(token)}` : ''}`
}

'use client'

import { useEffect, useState } from 'react'
import { dashboardApi } from '@/lib/api'
import type { TodayAttendance, MonthlyAverage, TardinessReport } from '@/types'
import { Card } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Users, UserCheck, UserX, TrendingUp } from 'lucide-react'

function MetricCard({
  icon: Icon,
  label,
  value,
  sub,
}: {
  icon: React.ElementType
  label: string
  value: string | number
  sub?: string
}) {
  return (
    <Card className="p-5 flex items-start gap-4">
      <div className="rounded-md bg-primary/10 p-2">
        <Icon className="size-5 text-primary" />
      </div>
      <div>
        <p className="text-sm text-muted-foreground">{label}</p>
        <p className="text-2xl font-bold">{value}</p>
        {sub && <p className="text-xs text-muted-foreground mt-0.5">{sub}</p>}
      </div>
    </Card>
  )
}

export default function DashboardPage() {
  const now = new Date()
  const [today, setToday] = useState<TodayAttendance | null>(null)
  const [monthly, setMonthly] = useState<MonthlyAverage | null>(null)
  const [tardiness, setTardiness] = useState<TardinessReport | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    Promise.all([
      dashboardApi.today(),
      dashboardApi.monthlyAverage(now.getMonth() + 1, now.getFullYear()),
      dashboardApi.tardiness(now.getMonth() + 1, now.getFullYear()),
    ])
      .then(([t, m, ta]) => {
        setToday(t)
        setMonthly(m)
        setTardiness(ta)
      })
      .finally(() => setLoading(false))
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  if (loading) {
    return (
      <div className="flex items-center justify-center h-48 text-muted-foreground text-sm">
        Cargando datos...
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <h1 className="text-xl font-semibold">Dashboard</h1>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <MetricCard
          icon={Users}
          label="Empleados activos"
          value={today?.total_active ?? '—'}
        />
        <MetricCard
          icon={UserCheck}
          label="Presentes hoy"
          value={today?.present ?? '—'}
          sub={today ? `${today.attendance_pct}% de asistencia` : undefined}
        />
        <MetricCard
          icon={UserX}
          label="Ausentes hoy"
          value={today?.absent ?? '—'}
        />
        <MetricCard
          icon={TrendingUp}
          label="Promedio mensual"
          value={monthly ? `${monthly.average_attendance_pct}%` : '—'}
          sub={monthly ? `${monthly.workdays} días hábiles` : undefined}
        />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card className="p-5">
          <h2 className="font-medium mb-3">Ausentes hoy</h2>
          {today?.absent_employees.length === 0 ? (
            <p className="text-sm text-muted-foreground">Todos presentes</p>
          ) : (
            <div className="space-y-2">
              {today?.absent_employees.map((emp) => (
                <div key={emp.id} className="flex items-center justify-between text-sm">
                  <span>{emp.name}</span>
                  {emp.department && (
                    <Badge variant="secondary">{emp.department}</Badge>
                  )}
                </div>
              ))}
            </div>
          )}
        </Card>

        <Card className="p-5">
          <h2 className="font-medium mb-3">Tardanzas del mes</h2>
          {!tardiness || tardiness.tardiness.length === 0 ? (
            <p className="text-sm text-muted-foreground">Sin tardanzas registradas</p>
          ) : (
            <div className="space-y-2">
              {tardiness.tardiness.slice(0, 5).map((entry) => (
                <div key={entry.employee_id} className="flex items-center justify-between text-sm">
                  <span>{entry.name}</span>
                  <div className="flex items-center gap-2">
                    {entry.department && (
                      <Badge variant="secondary">{entry.department}</Badge>
                    )}
                    <Badge variant="destructive">{entry.count}</Badge>
                  </div>
                </div>
              ))}
            </div>
          )}
        </Card>
      </div>
    </div>
  )
}

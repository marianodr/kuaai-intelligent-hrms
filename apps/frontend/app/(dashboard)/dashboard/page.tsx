'use client'

import { useEffect, useState } from 'react'
import { dashboardApi } from '@/lib/api'
import type { TodayAttendance, MonthlyAverage, TardinessReport, RecentEntry, MonthlyAbsences } from '@/types'
import { Card } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Table, TableHeader, TableBody, TableRow, TableHead, TableCell } from '@/components/ui/table'
import { PieChart, Pie, Cell } from 'recharts'

const RECURRING_TARDINESS_THRESHOLD = 3
const RECENT_ENTRIES_POLL_INTERVAL_MS = 20_000

function AttendanceDonutCard({ today }: { today: TodayAttendance | null }) {
  const present = today?.present ?? 0
  const absent = today?.absent ?? 0
  const total = present + absent
  const data = total > 0 ? [{ name: 'Presentes', value: present }, { name: 'Ausentes', value: absent }] : [{ name: 'Sin datos', value: 1 }]
  const colors = total > 0 ? ['#22c55e', '#ef4444'] : ['#e5e7eb']
  const presentPct = total > 0 ? Math.round((present / total) * 100) : 0
  const absentPct = total > 0 ? Math.round((absent / total) * 100) : 0

  return (
    <Card className="p-5">
      <p className="text-sm font-medium text-center">Asistencia del Día</p>
      <div className="flex flex-1 flex-col items-center justify-center gap-3">
        <PieChart width={120} height={120}>
          <Pie
            data={data}
            dataKey="value"
            innerRadius={35}
            outerRadius={55}
            startAngle={90}
            endAngle={-270}
            stroke="none"
          >
            {data.map((entry, i) => (
              <Cell key={entry.name} fill={colors[i]} />
            ))}
          </Pie>
        </PieChart>
        <div className="flex items-center justify-center gap-4 text-xs">
          <span className="flex items-center gap-1">
            <span className="size-2 rounded-full bg-green-500" />
            Presentes: <strong>{present}</strong> ({presentPct}%)
          </span>
          <span className="flex items-center gap-1">
            <span className="size-2 rounded-full bg-red-500" />
            Ausentes: <strong>{absent}</strong> ({absentPct}%)
          </span>
        </div>
      </div>
    </Card>
  )
}

function MonthlyAverageCard({ monthly }: { monthly: MonthlyAverage | null }) {
  return (
    <Card className="p-5">
      <p className="text-sm font-medium text-center">Promedio de Asistencia Mensual</p>
      <div className="flex flex-1 flex-col items-center justify-center gap-1 text-center">
        <p className="text-4xl font-bold text-primary">
          {monthly ? `${monthly.average_attendance_pct}%` : '—'}
        </p>
        <p className="text-xs text-muted-foreground">Mes actual</p>
        {monthly && (
          <p className="text-xs text-muted-foreground">
            {monthly.total_present} / {monthly.total_expected} asistencias
          </p>
        )}
      </div>
    </Card>
  )
}

function RecurringTardinessCard({ tardiness }: { tardiness: TardinessReport | null }) {
  const recurringCount =
    tardiness?.tardiness.filter((t) => t.count >= RECURRING_TARDINESS_THRESHOLD).length ?? 0

  return (
    <Card className="p-5">
      <p className="text-sm font-medium text-center">Tardanzas Recurrentes (Mes)</p>
      <div className="flex flex-1 flex-col items-center justify-center gap-1 text-center">
        <p className="text-4xl font-bold text-amber-500">{tardiness ? recurringCount : '—'}</p>
        <p className="text-xs text-muted-foreground">
          Empleados con {RECURRING_TARDINESS_THRESHOLD}+ tardanzas
        </p>
      </div>
    </Card>
  )
}

function RecentEntriesCard({ entries }: { entries: RecentEntry[] }) {
  return (
    <Card className="p-5">
      <h2 className="font-medium mb-3">Registro de hoy (Tiempo real)</h2>
      {entries.length === 0 ? (
        <p className="text-sm text-muted-foreground">Sin fichajes todavía hoy</p>
      ) : (
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Empleado</TableHead>
              <TableHead>Sector</TableHead>
              <TableHead>Fecha y hora</TableHead>
              <TableHead />
            </TableRow>
          </TableHeader>
          <TableBody>
            {entries.map((entry) => (
              <TableRow key={entry.id}>
                <TableCell>{entry.name}</TableCell>
                <TableCell>{entry.department ?? '—'}</TableCell>
                <TableCell>
                  {new Date(entry.timestamp).toLocaleString('es-AR', {
                    day: '2-digit',
                    month: '2-digit',
                    year: 'numeric',
                    hour: '2-digit',
                    minute: '2-digit',
                    hour12: false,
                  })}
                </TableCell>
                <TableCell>
                  {entry.is_late && <Badge variant="warning">Tardanza</Badge>}
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      )}
    </Card>
  )
}

function MonthlyAbsencesCard({ absences }: { absences: MonthlyAbsences | null }) {
  return (
    <Card className="p-5">
      <h2 className="font-medium mb-3">Ausencias del mes</h2>
      {!absences || absences.absences.length === 0 ? (
        <p className="text-sm text-muted-foreground">Sin ausencias registradas</p>
      ) : (
        <div className="space-y-2">
          {absences.absences.slice(0, 5).map((entry) => (
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
  )
}

export default function DashboardPage() {
  const now = new Date()
  const [today, setToday] = useState<TodayAttendance | null>(null)
  const [monthly, setMonthly] = useState<MonthlyAverage | null>(null)
  const [tardiness, setTardiness] = useState<TardinessReport | null>(null)
  const [absences, setAbsences] = useState<MonthlyAbsences | null>(null)
  const [recentEntries, setRecentEntries] = useState<RecentEntry[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    Promise.all([
      dashboardApi.today(),
      dashboardApi.monthlyAverage(now.getMonth() + 1, now.getFullYear()),
      dashboardApi.tardiness(now.getMonth() + 1, now.getFullYear()),
      dashboardApi.monthlyAbsences(now.getMonth() + 1, now.getFullYear()),
      dashboardApi.recentEntries(),
    ])
      .then(([t, m, ta, ab, re]) => {
        setToday(t)
        setMonthly(m)
        setTardiness(ta)
        setAbsences(ab)
        setRecentEntries(re)
      })
      .finally(() => setLoading(false))
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  useEffect(() => {
    const interval = setInterval(() => {
      dashboardApi.recentEntries().then(setRecentEntries).catch(() => {})
    }, RECENT_ENTRIES_POLL_INTERVAL_MS)
    return () => clearInterval(interval)
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

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        <AttendanceDonutCard today={today} />
        <MonthlyAverageCard monthly={monthly} />
        <RecurringTardinessCard tardiness={tardiness} />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <RecentEntriesCard entries={recentEntries} />

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
                    <Badge variant="warning">{entry.count}</Badge>
                  </div>
                </div>
              ))}
            </div>
          )}
        </Card>

        <MonthlyAbsencesCard absences={absences} />
      </div>
    </div>
  )
}

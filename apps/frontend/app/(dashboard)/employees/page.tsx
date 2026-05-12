'use client'

import { useEffect, useState, useCallback } from 'react'
import { employeesApi } from '@/lib/api'
import type { Employee, CreateEmployeeDto, UpdateEmployeeDto } from '@/types'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Badge } from '@/components/ui/badge'
import { Card } from '@/components/ui/card'
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from '@/components/ui/table'
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger, DialogFooter,
} from '@/components/ui/dialog'
import { Plus, Search, Pencil, UserX } from 'lucide-react'

const EMPTY_FORM: CreateEmployeeDto = {
  first_name: '', last_name: '', email: '', legajo: '', rfid_code: '', department: '',
}

export default function EmployeesPage() {
  const [employees, setEmployees] = useState<Employee[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [search, setSearch] = useState('')
  const [department, setDepartment] = useState('')
  const [loading, setLoading] = useState(true)

  const [createOpen, setCreateOpen] = useState(false)
  const [editTarget, setEditTarget] = useState<Employee | null>(null)
  const [form, setForm] = useState<CreateEmployeeDto>(EMPTY_FORM)
  const [saving, setSaving] = useState(false)
  const [formError, setFormError] = useState('')

  const limit = 10

  const fetchEmployees = useCallback(async () => {
    setLoading(true)
    try {
      const res = await employeesApi.list(page, limit, search || undefined, department || undefined)
      setEmployees(res.data)
      setTotal(res.total)
    } finally {
      setLoading(false)
    }
  }, [page, search, department])

  useEffect(() => { fetchEmployees() }, [fetchEmployees])

  function openCreate() {
    setForm(EMPTY_FORM)
    setFormError('')
    setCreateOpen(true)
  }

  function openEdit(emp: Employee) {
    setForm({
      first_name: emp.first_name,
      last_name: emp.last_name,
      email: emp.email ?? '',
      legajo: emp.legajo,
      rfid_code: emp.rfid_code,
      department: emp.department ?? '',
    })
    setFormError('')
    setEditTarget(emp)
  }

  async function handleSave() {
    setSaving(true)
    setFormError('')
    try {
      const dto = { ...form, email: form.email || undefined, department: form.department || undefined }
      if (editTarget) {
        const updated: UpdateEmployeeDto = dto
        await employeesApi.update(editTarget.id, updated)
        setEditTarget(null)
      } else {
        await employeesApi.create(dto)
        setCreateOpen(false)
      }
      fetchEmployees()
    } catch (e: unknown) {
      setFormError(e instanceof Error ? e.message : 'Error al guardar')
    } finally {
      setSaving(false)
    }
  }

  async function handleDeactivate(id: number) {
    if (!confirm('¿Desactivar este empleado?')) return
    await employeesApi.deactivate(id)
    fetchEmployees()
  }

  const totalPages = Math.ceil(total / limit)

  function EmployeeForm() {
    return (
      <div className="space-y-3">
        <div className="grid grid-cols-2 gap-3">
          <div className="space-y-1">
            <Label>Nombre</Label>
            <Input value={form.first_name} onChange={(e) => setForm({ ...form, first_name: e.target.value })} required />
          </div>
          <div className="space-y-1">
            <Label>Apellido</Label>
            <Input value={form.last_name} onChange={(e) => setForm({ ...form, last_name: e.target.value })} required />
          </div>
        </div>
        <div className="space-y-1">
          <Label>Email</Label>
          <Input type="email" value={form.email ?? ''} onChange={(e) => setForm({ ...form, email: e.target.value })} />
        </div>
        <div className="grid grid-cols-2 gap-3">
          <div className="space-y-1">
            <Label>Legajo</Label>
            <Input value={form.legajo} onChange={(e) => setForm({ ...form, legajo: e.target.value })} required />
          </div>
          <div className="space-y-1">
            <Label>Código RFID</Label>
            <Input value={form.rfid_code} onChange={(e) => setForm({ ...form, rfid_code: e.target.value })} required />
          </div>
        </div>
        <div className="space-y-1">
          <Label>Departamento</Label>
          <Input value={form.department ?? ''} onChange={(e) => setForm({ ...form, department: e.target.value })} />
        </div>
        {formError && <p className="text-sm text-destructive">{formError}</p>}
      </div>
    )
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold">Empleados</h1>
        <Dialog open={createOpen} onOpenChange={setCreateOpen}>
          <DialogTrigger render={<Button onClick={openCreate} />}>
            <Plus />
            Nuevo empleado
          </DialogTrigger>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Nuevo empleado</DialogTitle>
            </DialogHeader>
            <EmployeeForm />
            <DialogFooter>
              <Button onClick={handleSave} disabled={saving}>
                {saving ? 'Guardando...' : 'Crear empleado'}
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </div>

      <Card className="p-4">
        <div className="flex gap-2 mb-4">
          <div className="relative flex-1">
            <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 size-4 text-muted-foreground" />
            <Input
              placeholder="Buscar por nombre..."
              className="pl-8"
              value={search}
              onChange={(e) => { setSearch(e.target.value); setPage(1) }}
            />
          </div>
          <Input
            placeholder="Departamento"
            className="w-44"
            value={department}
            onChange={(e) => { setDepartment(e.target.value); setPage(1) }}
          />
        </div>

        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Nombre</TableHead>
              <TableHead>Legajo</TableHead>
              <TableHead>Departamento</TableHead>
              <TableHead>Estado</TableHead>
              <TableHead className="text-right">Acciones</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {loading ? (
              <TableRow>
                <TableCell colSpan={5} className="text-center text-muted-foreground py-8">
                  Cargando...
                </TableCell>
              </TableRow>
            ) : employees.length === 0 ? (
              <TableRow>
                <TableCell colSpan={5} className="text-center text-muted-foreground py-8">
                  Sin resultados
                </TableCell>
              </TableRow>
            ) : (
              employees.map((emp) => (
                <TableRow key={emp.id}>
                  <TableCell>
                    <p className="font-medium">{emp.first_name} {emp.last_name}</p>
                    {emp.email && <p className="text-xs text-muted-foreground">{emp.email}</p>}
                  </TableCell>
                  <TableCell className="font-mono text-sm">{emp.legajo}</TableCell>
                  <TableCell>{emp.department ?? '—'}</TableCell>
                  <TableCell>
                    <Badge variant={emp.status === 'ACTIVO' ? 'default' : 'secondary'}>
                      {emp.status}
                    </Badge>
                  </TableCell>
                  <TableCell className="text-right">
                    <div className="flex justify-end gap-1">
                      <Dialog open={editTarget?.id === emp.id} onOpenChange={(o) => !o && setEditTarget(null)}>
                        <DialogTrigger render={<Button variant="ghost" size="icon" onClick={() => openEdit(emp)} />}>
                          <Pencil />
                        </DialogTrigger>
                        <DialogContent>
                          <DialogHeader>
                            <DialogTitle>Editar empleado</DialogTitle>
                          </DialogHeader>
                          <EmployeeForm />
                          <DialogFooter>
                            <Button onClick={handleSave} disabled={saving}>
                              {saving ? 'Guardando...' : 'Guardar cambios'}
                            </Button>
                          </DialogFooter>
                        </DialogContent>
                      </Dialog>
                      {emp.status === 'ACTIVO' && (
                        <Button
                          variant="ghost"
                          size="icon"
                          onClick={() => handleDeactivate(emp.id)}
                          title="Desactivar"
                        >
                          <UserX className="text-destructive" />
                        </Button>
                      )}
                    </div>
                  </TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>

        {totalPages > 1 && (
          <div className="flex items-center justify-between mt-4 text-sm text-muted-foreground">
            <span>{total} empleados en total</span>
            <div className="flex gap-2">
              <Button
                variant="outline"
                size="sm"
                disabled={page === 1}
                onClick={() => setPage((p) => p - 1)}
              >
                Anterior
              </Button>
              <span className="flex items-center px-2">
                {page} / {totalPages}
              </span>
              <Button
                variant="outline"
                size="sm"
                disabled={page === totalPages}
                onClick={() => setPage((p) => p + 1)}
              >
                Siguiente
              </Button>
            </div>
          </div>
        )}
      </Card>
    </div>
  )
}

'use client'

import { useEffect, useState, useCallback } from 'react'
import { usersApi } from '@/lib/api'
import { getUser } from '@/lib/auth'
import type { HrUser } from '@/types'
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
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from '@/components/ui/select'
import { Plus, Pencil, UserX, ShieldAlert } from 'lucide-react'

const EMPTY_FORM = { email: '', password: '', role: 'rrhh' as 'admin' | 'rrhh' }

export default function AdminUsersPage() {
  const currentUser = getUser()
  const [users, setUsers]             = useState<HrUser[]>([])
  const [loading, setLoading]         = useState(true)
  const [createOpen, setCreateOpen]   = useState(false)
  const [editTarget, setEditTarget]   = useState<HrUser | null>(null)
  const [form, setForm]               = useState(EMPTY_FORM)
  const [saving, setSaving]           = useState(false)
  const [formError, setFormError]     = useState('')

  const fetchUsers = useCallback(async () => {
    setLoading(true)
    try {
      setUsers(await usersApi.list())
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { fetchUsers() }, [fetchUsers])

  if (currentUser?.role !== 'admin') {
    return (
      <div className="flex flex-col items-center justify-center h-64 gap-3 text-muted-foreground">
        <ShieldAlert className="size-10 opacity-40" />
        <p>Solo los administradores pueden acceder a esta sección.</p>
      </div>
    )
  }

  function openCreate() {
    setForm(EMPTY_FORM)
    setFormError('')
    setCreateOpen(true)
  }

  function openEdit(u: HrUser) {
    setForm({ email: u.email, password: '', role: u.role })
    setFormError('')
    setEditTarget(u)
  }

  async function handleSave() {
    setSaving(true)
    setFormError('')
    try {
      if (editTarget) {
        const dto: Record<string, unknown> = { email: form.email, role: form.role }
        if (form.password) dto.password = form.password
        await usersApi.update(editTarget.id, dto)
        setEditTarget(null)
      } else {
        await usersApi.create(form.email, form.password, form.role)
        setCreateOpen(false)
      }
      fetchUsers()
    } catch (e: unknown) {
      setFormError(e instanceof Error ? e.message : 'Error al guardar')
    } finally {
      setSaving(false)
    }
  }

  async function handleDeactivate(id: number) {
    if (!confirm('¿Desactivar este usuario?')) return
    await usersApi.deactivate(id)
    fetchUsers()
  }

  function UserForm({ isEdit = false }: { isEdit?: boolean }) {
    return (
      <div className="space-y-3">
        <div className="space-y-1">
          <Label>Email</Label>
          <Input
            type="email"
            value={form.email}
            onChange={(e) => setForm({ ...form, email: e.target.value })}
            required
          />
        </div>
        <div className="space-y-1">
          <Label>{isEdit ? 'Nueva contraseña (dejar vacío para no cambiar)' : 'Contraseña'}</Label>
          <Input
            type="password"
            value={form.password}
            onChange={(e) => setForm({ ...form, password: e.target.value })}
            required={!isEdit}
            autoComplete="new-password"
          />
        </div>
        <div className="space-y-1">
          <Label>Rol</Label>
          <Select
            value={form.role}
            onValueChange={(v) => setForm({ ...form, role: v as 'admin' | 'rrhh' })}
          >
            <SelectTrigger>
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="rrhh">RRHH</SelectItem>
              <SelectItem value="admin">Admin</SelectItem>
            </SelectContent>
          </Select>
        </div>
        {formError && <p className="text-sm text-destructive">{formError}</p>}
      </div>
    )
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold">Usuarios del sistema</h1>
        <Dialog open={createOpen} onOpenChange={setCreateOpen}>
          <DialogTrigger render={<Button onClick={openCreate} />}>
            <Plus />
            Nuevo usuario
          </DialogTrigger>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Nuevo usuario</DialogTitle>
            </DialogHeader>
            <UserForm />
            <DialogFooter>
              <Button onClick={handleSave} disabled={saving}>
                {saving ? 'Creando...' : 'Crear usuario'}
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </div>

      <Card className="p-0 overflow-hidden">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Email</TableHead>
              <TableHead>Rol</TableHead>
              <TableHead>Estado</TableHead>
              <TableHead>Creado</TableHead>
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
            ) : users.length === 0 ? (
              <TableRow>
                <TableCell colSpan={5} className="text-center text-muted-foreground py-8">
                  Sin usuarios
                </TableCell>
              </TableRow>
            ) : (
              users.map((u) => (
                <TableRow key={u.id}>
                  <TableCell className="font-medium">{u.email}</TableCell>
                  <TableCell>
                    <Badge variant={u.role === 'admin' ? 'default' : 'secondary'}>
                      {u.role === 'admin' ? 'Admin' : 'RRHH'}
                    </Badge>
                  </TableCell>
                  <TableCell>
                    <Badge variant={u.is_active ? 'default' : 'secondary'}>
                      {u.is_active ? 'Activo' : 'Inactivo'}
                    </Badge>
                  </TableCell>
                  <TableCell className="text-sm text-muted-foreground">
                    {new Date(u.created_at).toLocaleDateString('es-AR')}
                  </TableCell>
                  <TableCell className="text-right">
                    <div className="flex justify-end gap-1">
                      <Dialog
                        open={editTarget?.id === u.id}
                        onOpenChange={(o) => !o && setEditTarget(null)}
                      >
                        <DialogTrigger render={
                          <Button variant="ghost" size="icon" onClick={() => openEdit(u)} />
                        }>
                          <Pencil />
                        </DialogTrigger>
                        <DialogContent>
                          <DialogHeader>
                            <DialogTitle>Editar usuario</DialogTitle>
                          </DialogHeader>
                          <UserForm isEdit />
                          <DialogFooter>
                            <Button onClick={handleSave} disabled={saving}>
                              {saving ? 'Guardando...' : 'Guardar cambios'}
                            </Button>
                          </DialogFooter>
                        </DialogContent>
                      </Dialog>
                      {u.is_active && u.id !== currentUser?.id && (
                        <Button
                          variant="ghost"
                          size="icon"
                          onClick={() => handleDeactivate(u.id)}
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
      </Card>
    </div>
  )
}

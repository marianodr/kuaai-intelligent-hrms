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
import { Plus, Pencil, UserX, RotateCcw, ShieldAlert, Eye, EyeOff } from 'lucide-react'

const EMPTY_FORM = { email: '', password: '', confirmPassword: '' }

type UserFormState = typeof EMPTY_FORM

function PasswordField({
  label,
  value,
  onChange,
  required,
}: {
  label: string
  value: string
  onChange: (value: string) => void
  required?: boolean
}) {
  const [visible, setVisible] = useState(false)
  return (
    <div className="space-y-1">
      <Label>{label}</Label>
      <div className="relative">
        <Input
          type={visible ? 'text' : 'password'}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          required={required}
          autoComplete="new-password"
          className="pr-9"
        />
        <button
          type="button"
          tabIndex={-1}
          onClick={() => setVisible((v) => !v)}
          className="absolute right-2 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
        >
          {visible ? <EyeOff className="size-4" /> : <Eye className="size-4" />}
        </button>
      </div>
    </div>
  )
}

function UserForm({
  form,
  setForm,
  formError,
  isEdit = false,
  isAdminTarget = false,
}: {
  form: UserFormState
  setForm: (form: UserFormState) => void
  formError: string
  isEdit?: boolean
  isAdminTarget?: boolean
}) {
  const passwordRequired = !isEdit || isAdminTarget

  return (
    <div className="space-y-3">
      <div className="space-y-1">
        <Label>Email</Label>
        <Input
          type="email"
          value={form.email}
          onChange={(e) => setForm({ ...form, email: e.target.value })}
          disabled={isAdminTarget}
          required
        />
      </div>
      <PasswordField
        label={
          isAdminTarget
            ? 'Nueva contraseña'
            : isEdit
              ? 'Nueva contraseña (dejar vacío para no cambiar)'
              : 'Contraseña'
        }
        value={form.password}
        onChange={(v) => setForm({ ...form, password: v })}
        required={passwordRequired}
      />
      <PasswordField
        label="Repetir contraseña"
        value={form.confirmPassword}
        onChange={(v) => setForm({ ...form, confirmPassword: v })}
        required={passwordRequired}
      />
      {formError && <p className="text-sm text-destructive">{formError}</p>}
    </div>
  )
}

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
    setForm({ email: u.email, password: '', confirmPassword: '' })
    setFormError('')
    setEditTarget(u)
  }

  async function handleSave() {
    setFormError('')
    const isAdminTarget = editTarget?.role === 'admin'
    const passwordRequired = !editTarget || isAdminTarget

    if (passwordRequired && !form.password) {
      setFormError('La contraseña es obligatoria')
      return
    }
    if (form.password && form.password !== form.confirmPassword) {
      setFormError('Las contraseñas no coinciden')
      return
    }

    setSaving(true)
    try {
      if (editTarget) {
        const dto: Record<string, unknown> = {}
        if (!isAdminTarget) dto.email = form.email
        if (form.password) dto.password = form.password
        await usersApi.update(editTarget.id, dto)
        setEditTarget(null)
      } else {
        await usersApi.create(form.email, form.password)
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

  async function handleReactivate(id: number) {
    await usersApi.reactivate(id)
    fetchUsers()
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
              <DialogTitle>Nuevo usuario de RRHH</DialogTitle>
            </DialogHeader>
            <UserForm form={form} setForm={setForm} formError={formError} />
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
              users.map((u) => {
                const isAdminTarget = u.role === 'admin'
                return (
                  <TableRow key={u.id}>
                    <TableCell className="font-medium">{u.email}</TableCell>
                    <TableCell>
                      <Badge variant={isAdminTarget ? 'default' : 'secondary'}>
                        {isAdminTarget ? 'Admin' : 'RRHH'}
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
                              <DialogTitle>
                                {isAdminTarget ? 'Cambiar contraseña de administrador' : 'Editar usuario'}
                              </DialogTitle>
                            </DialogHeader>
                            <UserForm
                              form={form}
                              setForm={setForm}
                              formError={formError}
                              isEdit
                              isAdminTarget={isAdminTarget}
                            />
                            <DialogFooter>
                              <Button onClick={handleSave} disabled={saving}>
                                {saving ? 'Guardando...' : 'Guardar cambios'}
                              </Button>
                            </DialogFooter>
                          </DialogContent>
                        </Dialog>
                        {!isAdminTarget && (
                          u.is_active ? (
                            <Button
                              variant="ghost"
                              size="icon"
                              onClick={() => handleDeactivate(u.id)}
                              title="Desactivar"
                            >
                              <UserX className="text-destructive" />
                            </Button>
                          ) : (
                            <Button
                              variant="ghost"
                              size="icon"
                              onClick={() => handleReactivate(u.id)}
                              title="Reactivar"
                            >
                              <RotateCcw className="text-primary" />
                            </Button>
                          )
                        )}
                      </div>
                    </TableCell>
                  </TableRow>
                )
              })
            )}
          </TableBody>
        </Table>
      </Card>
    </div>
  )
}

# DESIGN.md — Guía de Diseño Kuaai Intelligent HRMS

## Filosofía de diseño

Minimalismo funcional: cada elemento en pantalla tiene un propósito. Se elimina el ruido visual para que el usuario pueda enfocarse en los datos y las acciones. El diseño transmite confianza, claridad y tecnología.

---

## Identidad visual

### Logo

- **Archivo:** `apps/frontend/public/logo.png`
- **Uso en código:** `<Image src="/logo.png" alt="Kuaai Intelligent HRMS" />`
- **Variantes:**
  - Completo (ícono + texto "Kuaai" + "Intelligent HRMS"): sidebar, login, onboarding
  - Solo ícono (cabeza con circuito): navbar colapsada, favicon, loading states
- **Espacio mínimo:** 16px de padding alrededor del logo en todos los contextos
- **Fondo:** siempre blanco (`#FFFFFF`) o transparente; nunca sobre fondos oscuros

---

## Paleta de colores

| Token              | Valor     | Uso                                                      |
|--------------------|-----------|----------------------------------------------------------|
| `primary`          | `#0072D5` | CTAs, links activos, íconos de acción, indicadores       |
| `primary-hover`    | `#005BB5` | Estado hover/focus de elementos primarios                |
| `primary-light`    | `#E6F0FB` | Fondos de secciones destacadas, badges, chips            |
| `white`            | `#FFFFFF` | Fondo base de toda la aplicación, cards, modales         |
| `surface`          | `#F8FAFC` | Fondo alternativo (sidebar, headers de tabla)            |
| `border`           | `#E2E8F0` | Bordes de cards, inputs, divisores                       |
| `text-primary`     | `#0F172A` | Títulos, texto principal                                 |
| `text-secondary`   | `#64748B` | Subtítulos, labels, texto de ayuda                       |
| `text-disabled`    | `#CBD5E1` | Placeholders, elementos deshabilitados                   |
| `success`          | `#16A34A` | Estados positivos (asistencia OK, documento procesado)   |
| `warning`          | `#D97706` | Alertas no críticas (tardanza, documento pendiente)      |
| `error`            | `#DC2626` | Errores, validaciones fallidas, ausencias                |

### Uso en Tailwind CSS

```js
// tailwind.config.ts
colors: {
  primary: {
    DEFAULT: '#0072D5',
    hover:   '#005BB5',
    light:   '#E6F0FB',
  },
  surface: '#F8FAFC',
}
```

---

## Tipografía

| Rol           | Familia          | Peso      | Tamaño (rem) |
|---------------|------------------|-----------|--------------|
| Display       | Inter            | 700       | 2.25 (36px)  |
| H1            | Inter            | 700       | 1.875 (30px) |
| H2            | Inter            | 600       | 1.5 (24px)   |
| H3            | Inter            | 600       | 1.25 (20px)  |
| Body          | Inter            | 400       | 1 (16px)     |
| Body small    | Inter            | 400       | 0.875 (14px) |
| Label / Chip  | Inter            | 500       | 0.75 (12px)  |
| Monospace     | JetBrains Mono   | 400       | 0.875 (14px) |

- **Interlineado base:** 1.5
- **Letter spacing títulos:** -0.025em (tight)
- **Carga en Next.js:** `next/font/google` con `display: 'swap'`

---

## Espaciado

Sistema de 8pt grid. Todos los valores de margen, padding y gap deben ser múltiplos de 4px.

| Token   | Valor |
|---------|-------|
| `xs`    | 4px   |
| `sm`    | 8px   |
| `md`    | 16px  |
| `lg`    | 24px  |
| `xl`    | 32px  |
| `2xl`   | 48px  |
| `3xl`   | 64px  |

---

## Componentes

### Botones

```
Primary:   bg-primary text-white          → hover: bg-primary-hover
Secondary: bg-white border border-primary text-primary → hover: bg-primary-light
Ghost:     text-primary                   → hover: bg-primary-light
Danger:    bg-error text-white
```

- **Border radius:** `rounded-lg` (8px)
- **Padding:** `px-4 py-2` (button md) / `px-3 py-1.5` (button sm)
- **Sin sombras** en botones; solo cambio de color en hover

### Cards

```
bg-white rounded-xl border border-border shadow-none
p-6 (padding interno estándar)
```

- Sin sombras por defecto; `shadow-sm` solo en cards interactivas al hover
- Separación entre cards: `gap-6`

### Inputs

```
border border-border rounded-lg px-3 py-2
focus: border-primary ring-2 ring-primary-light outline-none
text-text-primary placeholder:text-text-disabled
```

### Badges / Chips de estado

| Estado       | Clases                                        |
|--------------|-----------------------------------------------|
| Activo       | `bg-green-50 text-green-700 border-green-200` |
| Pendiente    | `bg-yellow-50 text-yellow-700 border-yellow-200` |
| Inactivo     | `bg-slate-100 text-slate-500 border-slate-200` |
| Error        | `bg-red-50 text-red-700 border-red-200`        |

- `text-xs font-medium px-2 py-0.5 rounded-full border`

### Sidebar

```
bg-white border-r border-border w-64 (expandida) / w-16 (colapsada)
```

- Logo en la parte superior con 24px de padding
- Ítem activo: `bg-primary-light text-primary font-medium rounded-lg`
- Ítem inactivo: `text-text-secondary hover:bg-surface`
- Ícono: 20px, alineado a la izquierda del label con 12px de gap

### Tabla de datos

```
Cabecera: bg-surface text-text-secondary text-xs font-medium uppercase tracking-wide
Fila:     border-b border-border hover:bg-surface transition-colors
```

- Sin bordes verticales en celdas
- Primera columna puede tener `font-medium text-text-primary`

---

## Iconografía

- **Librería:** Lucide React (`lucide-react`)
- **Tamaño estándar:** 20px (`size={20}`)
- **Tamaño en navbar/sidebar colapsado:** 24px
- **Color:** heredar del contexto (`currentColor`)
- **Stroke width:** 1.5 (valor por defecto de Lucide)

---

## Layout

### Estructura global

```
┌─────────────────────────────────────────────┐
│  Sidebar (64px colapsado / 256px expandido) │
│  ┌──────────────────────────────────────┐   │
│  │  Navbar top (64px alto, bg-white)    │   │
│  ├──────────────────────────────────────┤   │
│  │  Main content (flex-1, bg-surface)   │   │
│  │  max-w-7xl mx-auto px-6 py-8        │   │
│  └──────────────────────────────────────┘   │
└─────────────────────────────────────────────┘
```

### Breakpoints

| Nombre | Valor  | Comportamiento                              |
|--------|--------|---------------------------------------------|
| `sm`   | 640px  | Móvil → sidebar se convierte en drawer      |
| `md`   | 768px  | Tablet → sidebar colapsada por defecto       |
| `lg`   | 1024px | Desktop → sidebar expandida por defecto      |
| `xl`   | 1280px | Wide → contenido centrado con max-width      |

---

## Pantallas principales

### Login

- Fondo: `bg-white`
- Card central: `max-w-sm`, centrada vertical y horizontalmente
- Logo completo en la parte superior del card (80px de alto)
- Sin imágenes decorativas ni gradientes
- Un solo campo email + contraseña + botón primary full-width

### Dashboard

- Grid de KPI cards en la parte superior: 4 columnas en desktop, 2 en tablet, 1 en móvil
- KPI card: número grande en `text-primary`, label en `text-text-secondary`
- Gráfico de asistencia debajo de los KPIs (línea azul sobre fondo blanco)

### Módulo de empleados

- Tabla con búsqueda y filtros en la parte superior
- Avatar con iniciales en fondo `primary-light`, texto `primary`
- Badge de estado (activo/inactivo) en columna dedicada

### Agente RAG (chat)

- Layout de dos columnas: historial de conversaciones (izquierda) + chat activo (derecha)
- Mensajes del usuario: alineados a la derecha, `bg-primary text-white rounded-2xl rounded-tr-sm`
- Respuestas del agente: alineadas a la izquierda, `bg-surface border border-border rounded-2xl rounded-tl-sm`
- Input fijo en la parte inferior con botón de envío en `primary`

---

## Principios de implementación

1. **Blanco como base:** el fondo de la aplicación siempre es blanco o `surface` (#F8FAFC). Sin fondos oscuros ni gradientes en el layout principal.
2. **Azul con propósito:** `#0072D5` solo para acciones, estados activos y datos destacados. No decorativo.
3. **Sin sombras pesadas:** `shadow-sm` como máximo. Preferir bordes (`border`) para separar elementos.
4. **Densidad controlada:** las pantallas de gestión (tablas, formularios) deben respirar. Mínimo `gap-4` entre elementos.
5. **Estados visibles:** todo elemento interactivo debe tener estado hover, focus y disabled claramente definidos.
6. **Mobile-first:** diseñar primero para móvil y escalar hacia desktop.

---

## Assets

| Archivo                            | Uso                                      |
|------------------------------------|------------------------------------------|
| `apps/frontend/public/logo.png`    | Logo completo (navbar, login, docs)      |
| `apps/frontend/public/favicon.ico` | Favicon (generar desde el ícono del logo)|

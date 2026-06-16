# Fase 7 — Atomización de sprint 1–4 en master y separación del deploy en Digital Ocean

## Lo que se implementó

El trabajo de los "sprints" 1 a 4 vivía en 4 commits monolíticos (uno por
sprint), cada uno mezclando varias features/fixes sin relación entre sí. Por
ejemplo, el commit de sprint 1 mezclaba un fix de recursión del agente, un fix
de encoding de archivos, el seeder de admin y un cambio de `.gitignore`; el de
sprint 4 mezclaba mejoras de IA con la guía de deploy en Digital Ocean.

Se reescribió ese historial completo como **13 commits atómicos aplicados
directamente sobre `master`** (uno por feature/fix, siguiendo Conventional
Commits), y se creó la rama **`feature/deploy-digitalocean`**, con base en el
`master` resultante, que contiene únicamente la guía de deploy.

```
master (13 commits atómicos: sprint 1-2-3-4 sin deploy)
        ↑
feature/deploy-digitalocean (+1 commit: guía de deploy)
```

Como ninguna rama estaba pusheada a `origin` (solo `master` está en el
remoto, y sin este trabajo), la reescritura no afectó historial compartido ni
requirió force-push. Las ramas `feature/sprint-1-2-3` y `feature/sprint-4`
(con el historial monolítico anterior) quedaron obsoletas y se eliminaron;
se conservan como tags `backup/*` por si hace falta recuperar algo.

## Decisiones técnicas tomadas

### Por qué atomizar en vez de mantener un commit por sprint

"Sprint" es una unidad de planificación (ver `docs/ideas-plan.md`), no una
unidad natural de cambio de código. Mezclar features no relacionadas en un
commit/rama dificulta revertir, cherry-pickear o hacer `git bisect` sobre una
sola de ellas — quedó demostrado en la práctica cuando hubo que separar el
deploy del resto de sprint 4 con cirugía de `git reset --soft`. Aplicar
Conventional Commits de forma estricta (un `feat`/`fix`/`docs`/`chore` por
commit) evita ese problema de raíz.

### Por qué el deploy queda en su propia rama y el resto va a `master`

`docs/ideas-plan.md` lista el deploy en Digital Ocean como ítem de prioridad
🟢 baja, sin relación funcional con el resto del trabajo. El resto de los
sprints (fixes, gestión de usuarios, hilos de conversación, observabilidad,
visor de PDF, mejoras de IA) ya está validado y se integra directamente a
`master`. El deploy queda aparte para poder iterarlo y probarlo contra un
Droplet real sin bloquear ni reabrir el resto del trabajo.

### Cómo se reconstruyó el historial

Para cada sprint, se llevó el árbol de trabajo al estado del commit objetivo
con `git checkout <commit> -- <paths>` y luego se hizo `git add`/`commit` por
grupos de archivos que pertenecen a la misma feature. Cuando un mismo archivo
mezclaba dos features (p. ej. `lib/api.ts` con cambios de hilos de
conversación y de CRUD de usuarios en el mismo commit original), se editó el
archivo manualmente para aplicar primero solo el fragmento de una feature, y
el resto en el commit siguiente. Después de reconstruir cada sprint se
verificó con `git diff <commit_original> master` (debe quedar vacío) antes de
seguir con el siguiente.

## Estructura de archivos (commits atómicos en `master`, en orden)

| # | Commit | Alcance |
|---|---|---|
| 1 | `fix: capturar GraphRecursionError...` | `routers/agent.py` |
| 2 | `fix: normalizar encoding...` | `routers/documents.py` |
| 3 | `feat: crear admin inicial...` | `seeder/*`, `.env.example`, `seed.sql`, README |
| 4 | `chore: ignorar notas de planificación...` | `.gitignore` |
| 5 | `feat: CRUD de usuarios RRHH...` | `users/*` (NestJS), `admin/users` (frontend), `sidebar.tsx`, parte de `lib/api.ts`/`types/index.ts` |
| 6 | `feat: incluir fuentes de documentos...` | `hrms_tools.py`, línea del system prompt en `agent_service.py` |
| 7 | `feat: hilos de conversación...` | `threads.py`, migración 002, `cleanup/*`, proxy de hilos, `chat/page.tsx`, resto de `lib/api.ts`/`types/index.ts`/`agent_service.py` |
| 8 | `feat: sistema de logs de auditoría` | `middleware/audit_log.py`, `logging.interceptor.ts`, migración 003 |
| 9 | `feat: visor de PDF...` | `minio_client.py` (`get_bytes`), endpoint de descarga, `PdfViewer.tsx`, `jwt.strategy.ts` |
| 10 | `docs: documentar lógica del seed...` | README |
| 11 | `feat: OCR configurable en Docling` | `.env.example`, `config.py`, `ingestion.py` |
| 12 | `feat: script de generación de PDFs de RRHH` | `scripts/generate_hr_docs.py`, README |
| 13 | `feat: script de evaluación...RAGAS` | `scripts/eval_rag.py`, `requirements-eval.txt`, README |

`feature/deploy-digitalocean` (sobre el `master` anterior):

```
docs/deploy-digitalocean.md
```

## Cómo probarlo

```bash
# Verificar que cada sprint quedó atomizado correctamente (debe estar vacío).
# Se usan hashes fijos de los commits-tope de cada sprint en master (no
# master~N, que se desincroniza apenas se agregan commits nuevos encima).
git diff c54079e cd3c2b8    # sprint 1 (commits 1-4)
git diff 68a2952 23a1ba1    # sprint 2 (commits 5-7)
git diff 89168d1 9eb0bbc    # sprint 3 (commits 8-10)
git diff e378731 2761f22    # sprint 4 mejoras IA (commits 11-13)

# Verificar que master no tiene el doc de deploy
git show --stat master | grep deploy   # sin resultados

# Verificar que la rama de deploy sí lo tiene
git log --oneline feature/deploy-digitalocean -1
```

## Problemas encontrados y soluciones

| Problema | Solución |
|---|---|
| Los commits de sprint mezclaban features no relacionadas (hasta 6 cambios distintos en un solo commit) | Reconstrucción manual archivo por archivo / hunk por hunk en 13 commits atómicos |
| Algunos archivos (`lib/api.ts`, `types/index.ts`, `agent_service.py`) mezclaban dos features en el mismo diff | Edición manual para separar el fragmento de cada feature en su commit correspondiente, verificando con `git diff` que el resultado final coincidiera exactamente con el commit original |
| Riesgo de perder trabajo al reescribir `master` | Tags `backup/master-stray-sprint1`, `backup/feature-sprint-1-2-3`, `backup/feature-sprint-4-old` y `backup/deploy-digitalocean-old` antes de empezar; nada estaba pusheado a `origin` |

## Pendientes para fases siguientes

- Adoptar esta convención (atomic commits + un feature/fix por commit) para
  todo el trabajo nuevo, en vez de agrupar por sprint.
- Eliminar los tags `backup/*` una vez confirmado que el nuevo historial es
  estable (no antes de la entrega del PFG).
- Validar `docs/deploy-digitalocean.md` ejecutándola contra un Droplet real.

# OPERATIX — Contexto de proyecto

> Documento de continuidad para Codex y otros agentes. Actualizar al cerrar cada fase
> o cuando cambien las decisiones de arquitectura.

## Estado actual

- Fecha de referencia: 2026-08-16.
- Fase activa: Fase 1 — fundación FastAPI/MySQL (pendiente de iniciar).
- Rama de trabajo: `feat/operatix-mvp-main`, basada en `main`.
- Rama remota original preservada: `feat/operatix-mvp`.
- Respaldo local: `backup/operatix-mvp-root-0f6aece`.
- No se ha hecho `push` de la rama reconstruida.

## Qué existe hoy

El MVP actual es un monolito modular en Python con:

- Dash y CLI como interfaces.
- LangChain/LangGraph con tool calling.
- Proveedores OpenAI, Anthropic y Google Gemini.
- Dominio de ventas validado con Pydantic.
- Persistencia en Excel y Google Sheets.
- Dashboard Plotly.
- Pruebas unitarias offline.

La arquitectura actual sirve como base de migración, pero Excel/Google Sheets no deben
seguir siendo la base transaccional principal del producto final.

## Decisiones vigentes

- El producto se llama OPERATIX.
- El objetivo es un MVP gratuito siempre que sea posible.
- La base de datos objetivo es **MySQL**, no PostgreSQL.
- El backend objetivo es FastAPI con SQLAlchemy y Alembic.
- El frontend objetivo es React + TypeScript + Tailwind + Recharts.
- Excel se usará para importación, exportación y procesamiento de archivos.
- El modelo nunca accede directamente a MySQL; solo utiliza tools controladas.
- Las operaciones destructivas requieren confirmación explícita.
- Telegram será el primer canal externo; WhatsApp y Discord quedan preparados, no
  implementados.
- Redis solo se agregará si aparece una necesidad demostrable.
- No introducir SAP, ERP, Power BI, RPA, multiagentes complejos ni infraestructura
  distribuida durante el MVP.

## Trabajo completado

- Revisión local del código y contraste con GitHub.
- Ruff, formato, pytest y Semgrep ejecutados sobre el MVP original.
- Detectados riesgos pendientes: conversación sin memoria entre turnos, monedas mezcladas,
  fórmulas en hojas de cálculo, idempotencia incompleta y cobertura de pruebas baja.
- Rama de trabajo nueva creada desde `main`.
- MVP original trasladado al working tree de la rama nueva.
- `PROJECT_CONTEXT.md` añadido para continuidad entre agentes.

## Trabajo pendiente

### Fase 0 — Git (completada localmente)

- Crear un commit cuyo padre sea `main`.
- Verificar historial, pruebas y estado limpio.
- No hacer push sin autorización explícita; la rama reconstruida aún no se ha publicado.

### Fase 1 — Fundación

- Crear `backend/`, `frontend/` y `storage/` de forma incremental.
- Añadir FastAPI, configuración por entorno y endpoint de salud.
- Añadir MySQL local con Docker Compose.
- Añadir SQLAlchemy y migraciones Alembic.

### Fase 2 — Seguridad

- Usuarios, roles, permisos, JWT, hash de contraseñas y auditoría.
- Validación de archivos y entradas externas.
- Dependencias de autorización reutilizables en la API y las tools.

### Fase 3 — Dominio y orquestador

- Clientes, productos, inventario y ventas en MySQL.
- Servicios y repositorios separados de las rutas HTTP.
- Tools con permisos, límites por solicitud, confirmación e idempotencia.
- Mantener soporte para conversación multironda.

### Fase 4 — Excel y reportes

- Almacenar archivos fuera de MySQL y sus metadatos dentro de MySQL.
- Importar, exportar, validar y analizar Excel con pandas/openpyxl/xlsxwriter.
- Reportes con métricas separadas por moneda.

### Fase 5 — Frontend y Telegram

- Dashboard React con ventas, clientes, productos, inventario, archivos, reportes y
  auditoría.
- Abstracción de canales y `TelegramChannel`.
- Usar polling local para evitar pagar hosting mientras se valida el MVP.

### Fase 6 — Calidad y entrega

- Tests unitarios, integración y flujos críticos.
- Ruff, Semgrep y CI.
- Documentación de arquitectura, configuración, costos y operación.

## Costos a vigilar

Sin costo de licencia esperado en desarrollo local: Python, FastAPI, React, SQLAlchemy,
Alembic, MySQL Community, pandas, openpyxl, xlsxwriter, Telegram Bot API y librerías de
autenticación.

Posibles costos: consumo de LLM cloud, hosting, MySQL administrado, almacenamiento de
archivos, dominio, webhook público de Telegram, cuotas excedidas de CI y observabilidad
administrada. No añadir esos servicios sin informar primero el costo y ofrecer una opción
local o gratuita cuando sea viable.

## Verificación recomendada

```powershell
uv run ruff check .
uv run ruff format --check .
uv run python -m pytest
semgrep scan --config p/python --config p/security-audit src tests
git status --short --branch
git log --oneline --decorate --graph --all
```

## Instrucción para el siguiente agente

Leer primero este archivo, `AGENTS.md`, `README.md` y `docs/`. Confirmar la rama activa y
el estado de Git antes de editar. Continuar por la primera tarea pendiente de la fase
activa. Mantener MySQL como decisión vigente, evitar secretos y no hacer push, migraciones
destructivas ni servicios con costo sin autorización explícita.

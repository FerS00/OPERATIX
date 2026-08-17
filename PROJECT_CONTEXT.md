# OPERATIX — Contexto de proyecto

> Documento de continuidad para Codex y otros agentes. Actualizar al cerrar cada fase
> o cuando cambien las decisiones de arquitectura.

## Estado actual

- Fecha de referencia: 2026-08-16.
- Fase activa: Fase 5 — frontend React y Telegram (Fase 4 completada localmente).
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
- Fase 1 implementada: FastAPI, configuración MySQL, SQLAlchemy, Alembic, Docker Compose,
  estructura inicial de frontend/storage y endpoint de salud.
- Dependencias de la Fase 1 bloqueadas en `uv.lock`.
- Verificaciones de Fase 1: 9 pruebas, Ruff, formato, Compose y Alembic offline.
- Fase 2 implementada: usuarios, roles, permisos, hash Argon2, JWT de corta duración y
  auditoría.
- El registro público solo asigna `USER`; las rutas de prueba RBAC cubren `READ` y `ADMIN`.
- Verificaciones de Fase 2: 11 pruebas, Ruff y formato; cobertura total aproximada del 66%.
- Fase 3 implementada: clientes, productos, inventario, ventas, servicios transaccionales y
  `AIOrchestrator` con `ToolRegistry` explícita.
- Las ventas usan el precio autoritativo del producto, bloquean/descuentan inventario,
  guardan hash de comando y protegen reintentos con `Idempotency-Key`.
- Verificaciones de Fase 3: 12 pruebas, Ruff, formato, Semgrep (0 hallazgos) y Alembic
  offline; cobertura total aproximada del 72%.
- Fase 4 implementada: `FileStorage` guarda binarios fuera de MySQL con nombres UUID,
  límites de tamaño, hash SHA-256 y escritura atómica; `FileRecord` persiste solo metadata.
- La API acepta `.xlsx`, `.csv` y `.tsv`, ofrece vista previa de solo lectura (máximo 5.000
  filas) y rechaza fórmulas de entrada. Los reportes agregan por moneda y exportan libros
  `Resumen`/`Ventas` sin fórmulas, con auditoría.
- Endpoints de archivos y reportes protegidos por `CREATE`, `READ`, `REPORTS` y `EXPORT`.
- `python-multipart` quedó fijado en `uv.lock`; no se añadió ningún servicio de pago.
- Verificaciones de Fase 4: 17 pruebas, Ruff y formato; cubren almacenamiento, preview,
  descarga y exportación separada por moneda.

## Trabajo pendiente

### Fase 0 — Git (completada localmente)

- Crear un commit cuyo padre sea `main`.
- Verificar historial, pruebas y estado limpio.
- No hacer push sin autorización explícita; la rama reconstruida aún no se ha publicado.

### Fase 1 — Fundación (completada localmente)

- Base FastAPI en `backend/app` con `/api/v1/health` y `/api/v1/health/ready`.
- Configuración por entorno con URL MySQL opcional y credenciales fuera del código.
- SQLAlchemy y Alembic configurados para `mysql+pymysql`.
- Dockerfile y Compose con MySQL Community 8.4 local.
- Estructuras `frontend/` y `storage/` creadas sin instalar herramientas frontend todavía.
- No se levantó ningún contenedor ni servicio administrado; costo de esta fase: cero.

### Fase 2 — Seguridad (completada localmente)

- Usuarios, roles, permisos, JWT, hash Argon2 y auditoría en `backend/app/security`.
- Validación de email y contraseña mediante Pydantic.
- Dependencias de autorización reutilizables en la API y futuras tools.
- Migración `0002_security` preparada para MySQL.
- No se añadieron servicios externos ni costos de infraestructura.

### Fase 3 — Dominio y orquestador (completada localmente)

- Modelos y migración `0003_business` para clientes, productos, inventario y ventas.
- Servicios transaccionales separados de las rutas HTTP.
- `AIOrchestrator` y `ToolRegistry` con `create_sale`, `get_sales`, `get_inventory` y
  `get_sales_summary`.
- Permisos, límite de una tool por instancia, auditoría e idempotencia por hash.
- La conexión de lenguaje natural/memoria multironda queda pendiente para una fase LLM.

### Fase 4 — Excel y reportes

- [completado] Almacenar archivos fuera de MySQL y sus metadatos dentro de MySQL.
- [completado] Validar y previsualizar `.xlsx`, `.csv` y `.tsv` sin mutar el dominio.
- [completado] Exportar reportes sin fórmulas, con métricas separadas por moneda.
- [pendiente] Importación confirmada de filas hacia clientes/productos/ventas; se mantiene
  separada para añadir confirmación humana e idempotencia por fila.

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
administrada. `python-multipart`, openpyxl y las herramientas locales de esta fase son
software libre y no agregan costo de licencia. No añadir servicios administrados sin
informar primero el costo y ofrecer una opción local o gratuita cuando sea viable.

## Verificación recomendada

```powershell
uv run ruff check .
uv run ruff format --check .
uv run python -m pytest
semgrep scan --config p/python --config p/security-audit backend src tests
git status --short --branch
git log --oneline --decorate --graph --all
```

## Instrucción para el siguiente agente

Leer primero este archivo, `AGENTS.md`, `README.md` y `docs/`. Confirmar la rama activa y
el estado de Git antes de editar. Continuar por la primera tarea pendiente de la fase
activa. Mantener MySQL como decisión vigente, evitar secretos y no hacer push, migraciones
destructivas ni servicios con costo sin autorización explícita. Antes de implementar la
importación Excel completa, definir confirmación humana, resolución de clientes/productos
y claves de idempotencia por fila.

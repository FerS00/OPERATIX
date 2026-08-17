# OPERATIX — Agente de Automatización Empresarial Conversacional

OPERATIX es un MVP que convierte pedidos escritos en transacciones estructuradas. En el
primer incremento reconoce una venta mediante tool calling, la guarda en Excel o Google
Sheets y actualiza un dashboard local.

> Estado: **Fases 1–4 de plataforma implementadas localmente**. El flujo Dash/CLI legado
> sigue disponible, y la API FastAPI ya tiene seguridad y dominio inicial en MySQL. Las
> llamadas a proveedores cloud requieren una clave con cuota disponible.

## Arquitectura resumida

```text
Dash / CLI
    ↓
SalesAgent (LangChain sobre LangGraph)
    ↓
OpenAI | Anthropic | Gemini
    ↓ tool calling validado con Pydantic
register_sale
    ↓
SalesRepository
    ├── Excel local
    └── Google Sheets
    ↓
Dashboard Plotly
```

El modelo nunca escribe directamente. Solo propone argumentos para una herramienta; el
dominio los valida, genera el identificador de transacción y delega la escritura al
adaptador seleccionado.

## Alcance del Paso 1

- Chat local construido con Dash.
- Proveedores de IA intercambiables: OpenAI, Anthropic y Google Gemini.
- Autenticación mediante variables de entorno o una clave temporal introducida en la UI.
- Tool calling validado con Pydantic.
- Excel listo para usar sin infraestructura; Google Sheets como adaptador opcional.
- Identificadores de transacción e idempotencia básica por solicitud.
- Resumen de transacciones, unidades e importe con Plotly.

## Estructura del repositorio

```text
src/operatix/
├── application/       Casos de uso, agente y selección de repositorios
├── domain/            Modelos y reglas de ventas
├── infrastructure/    Adaptadores Excel y Google Sheets
├── llm/               Proveedores OpenAI, Anthropic y Gemini
├── ports/             Contratos de persistencia
└── presentation/      CLI, aplicación Dash y dashboard
tests/                 Pruebas unitarias y flujo LangGraph sin consumo cloud
docs/                  Arquitectura, configuración, desarrollo y herramientas
```

## Inicio rápido

Requisitos: Python 3.12–3.14 y `uv`.

```powershell
uv sync
Copy-Item .env.example .env.local
```

Completa en `.env.local` la clave del proveedor que usarás. Las demás pueden quedar
vacías. El archivo está excluido de Git. Una suscripción de ChatGPT no incluye saldo de
API; OpenAI Platform necesita facturación o cuota propia.

### Interfaz web

```powershell
uv run operatix-web
```

Abre `http://127.0.0.1:8050`. Elige el proveedor, el método de autenticación y el
almacenamiento. La opción de clave temporal es apropiada únicamente para una ejecución
local de un solo usuario.

| Proveedor | Variable de clave | Variable de modelo |
|---|---|---|
| OpenAI | `OPENAI_API_KEY` | `OPENAI_MODEL` |
| Anthropic | `ANTHROPIC_API_KEY` | `ANTHROPIC_MODEL` |
| Google Gemini | `GOOGLE_API_KEY` | `GOOGLE_MODEL` |

Los nombres de modelo son configurables porque la disponibilidad depende de cada cuenta
y cambia con el tiempo.

### Paso 1 desde la terminal

```powershell
uv run operatix "Agrega una venta de 5 laptops por $2500 para el cliente Juan Perez" --provider openai
```

Por defecto se crea `data/operatix.xlsx`. En el ejemplo, `$2500` se interpreta como el
total porque no se indicó “cada una”; se guardan precio unitario `500.00` y total
`2500.00`.

## Base API y MySQL local

Las Fases 1–3 añaden una base ejecutable para la futura plataforma. El flujo Dash/CLI
legado continúa usando Excel o Google Sheets mientras se completa la migración de la UI,
pero el backend ya puede gestionar clientes, productos, inventario y ventas en MySQL.

Para ejecutar la API sin Docker:

```powershell
uv run uvicorn backend.app.main:app --reload
```

Prueba `http://127.0.0.1:8000/api/v1/health`. El endpoint `/api/v1/health/ready` requiere
que MySQL esté disponible.

Para levantar MySQL y la API con Docker Compose, copia `.env.example` a `.env.local`,
cambia las contraseñas locales y ejecuta:

```powershell
docker compose --env-file .env.local up --build
uv run alembic upgrade head
```

MySQL Community y el contenedor local no requieren un servicio administrado. El consumo
de los proveedores LLM, el hosting y un MySQL administrado sí pueden generar costos y no
se incorporarán sin informarlo.

## Autenticación y permisos iniciales

La Fase 2 incorpora usuarios, roles, permisos, hash Argon2, JWT y auditoría. El registro
siempre crea un usuario `USER`; los roles privilegiados no se aceptan desde el cliente.

Endpoints disponibles:

```text
POST /api/v1/auth/register
POST /api/v1/auth/login
GET  /api/v1/auth/me
GET  /api/v1/security/read-check
GET  /api/v1/security/admin-check
```

Configura `JWT_SECRET` con al menos 32 caracteres aleatorios antes de usar login. Las
contraseñas, tokens y secretos nunca se escriben en `audit_logs`.

## Dominio MySQL y tools controladas

La API de negocio utiliza servicios separados de las rutas y una `AIOrchestrator` que
solo ejecuta tools registradas. La tool `create_sale` exige `CREATE`, usa el precio
autoritativo del producto, descuenta inventario dentro de la misma transacción y requiere
un header `Idempotency-Key` de 8 a 255 caracteres.

Endpoints iniciales:

```text
POST /api/v1/customers          (CREATE)
GET  /api/v1/customers          (READ)
POST /api/v1/products           (CREATE)
GET  /api/v1/products           (READ)
GET  /api/v1/inventory          (READ)
PUT  /api/v1/inventory/{id}     (UPDATE)
POST /api/v1/sales              (CREATE + Idempotency-Key)
GET  /api/v1/sales              (READ)
GET  /api/v1/sales/summary      (REPORTS)
```

Repetir la misma clave con los mismos datos devuelve la venta existente; reutilizarla
con datos distintos devuelve conflicto y no duplica la transacción.

## Archivos Excel y reportes

La Fase 4 mantiene los binarios fuera de MySQL y guarda en la tabla `files` únicamente
metadatos, hash SHA-256, usuario y ruta relativa opaca. Los archivos se almacenan bajo
`storage/uploads` o `storage/exports`, con límite configurable y nombres internos
generados por el servidor. Se aceptan `.xlsx`, `.csv` y `.tsv`; la vista previa es de
solo lectura, acotada a 5.000 filas y rechaza fórmulas en los datos de entrada.

Endpoints protegidos:

```text
POST /api/v1/files/upload                (CREATE, multipart/form-data)
GET  /api/v1/files                       (READ)
POST /api/v1/files/{id}/excel/preview    (READ)
GET  /api/v1/files/{id}/download         (READ)
GET  /api/v1/reports/sales/summary       (REPORTS)
POST /api/v1/reports/sales/export        (EXPORT)
```

Los totales del reporte siempre se agrupan por código de moneda; nunca se suman USD,
PEN u otras monedas entre sí. El libro exportado no contiene fórmulas y neutraliza
valores de texto que puedan interpretarse como fórmulas por Excel.

## Google Sheets

1. Crea una cuenta de servicio en Google Cloud y habilita Google Sheets API.
2. Descarga su JSON a `.secrets/google-service-account.json`.
3. Comparte la hoja con el correo de la cuenta de servicio.
4. Define `GOOGLE_SHEETS_SPREADSHEET_ID` en `.env.local`.
5. Selecciona `Google Sheets` en la interfaz o usa `--backend google_sheets`.

El JSON de la cuenta de servicio y los libros con datos transaccionales nunca deben
subirse al repositorio.

## Comportamiento transaccional

- El texto debe contener cliente, producto, cantidad e importe.
- Un importe se considera **total** salvo que el usuario diga “cada uno”, “por unidad” o
  “precio unitario”.
- `$` se interpreta como USD y `S/` como PEN cuando no se especifica otro código.
- Cada solicitud genera su propio UUID; una repetición interna del mismo tool call no
  duplica la fila.
- Si falta un dato obligatorio, el agente debe pedirlo antes de escribir.

## Solución de problemas

### OpenAI responde `insufficient_quota`

La clave llegó correctamente a OpenAI, pero su proyecto no tiene saldo o alcanzó un
límite de gasto. Revisa la facturación y los límites de OpenAI Platform. La suscripción
de ChatGPT y la facturación de API son independientes.

### No aparece la venta en Google Sheets

Comprueba que Sheets API esté habilitada, que el ID sea correcto y que la hoja esté
compartida con el correo `client_email` de la cuenta de servicio.

### Excel está abierto en otra aplicación

Cierra el libro antes de procesar otra operación; Excel puede bloquear temporalmente la
escritura del archivo.

## Calidad

```powershell
uv run ruff check .
uv run ruff format --check .
uv run python -m pytest
semgrep scan --config p/python --config p/security-audit backend src tests
```

Consulta [la arquitectura](docs/ARCHITECTURE.md) y
[la configuración y seguridad](docs/CONFIGURATION.md),
[la guía de desarrollo](docs/DEVELOPMENT.md) y
[las recomendaciones de herramientas](docs/TOOLING.md).

## Límites conscientes del MVP

- La interfaz de clave temporal es solo para ejecución local de un usuario.
- No existe todavía aprobación humana para montos altos.
- Excel y Google Sheets no son adecuados para alta concurrencia.
- No hay webhook público, Telegram ni despliegue productivo.
- No se añadirá una cola o un servicio administrado hasta que las métricas reales lo
  justifiquen.

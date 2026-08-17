# Guía de desarrollo

## Preparación

```powershell
uv sync
Copy-Item .env.example .env.local
```

`uv.lock` fija las dependencias resueltas. Actualízalo de forma intencional y revisa los
cambios antes de publicarlos.

## Comandos cotidianos

```powershell
uv run operatix-web
uv run ruff check .
uv run ruff format --check .
uv run python -m pytest
uv run uvicorn backend.app.main:app --reload
```

En otra terminal, para ejecutar el dashboard:

```powershell
cd frontend
npm install
npm run dev
```

El build de entrega se valida con `npm run build`. No se versionan `node_modules/`,
`dist/` ni `frontend/.env.local`.

La guía completa para instalar y retirar el proyecto en una PC de prueba está en
[`docs/INSTALLATION.md`](INSTALLATION.md).

Para probar el CLI:

```powershell
uv run operatix "Agrega una venta de 2 monitores a $300 cada uno para Ana Torres"
```

### MySQL local y migraciones

Configura `.env.local` a partir de `.env.example` y ejecuta:

```powershell
docker compose --env-file .env.local up --build
uv run alembic upgrade head
```

La primera migración solo establece el historial; `0002_security` añade la seguridad,
`0003_business` crea las tablas iniciales del dominio y `0004_files` registra metadata de
archivos.

Las migraciones actuales llegan hasta `0004_files`. La ruta de ventas exige el header
`Idempotency-Key`; las pruebas de dominio usan SQLite temporal y no sustituyen una prueba
de integración contra MySQL antes de desplegar.

### Archivos y reportes

`backend.app.services.storage.FileStorage` escribe los bytes fuera de la base mediante un
archivo temporal y `os.replace`, calcula SHA-256 y asigna nombres UUID. `FileRecord` guarda
solo metadata en MySQL. `backend.app.services.excel.preview_file` lee `.xlsx`, `.csv` y
`.tsv` en modo acotado y sin mutar el dominio. `reports.export_sales_report` genera un
libro sin fórmulas, con hojas `Resumen` y `Ventas`, y registra su exportación en `files`
y `audit_logs`.

Para probar sin datos reales se usa `OPERATIX_STORAGE_ROOT` apuntando a una carpeta
temporal. Nunca coloques libros de clientes o reportes generados bajo control de versiones.

### Canales

`backend.app.channels.telegram.TelegramChannel` es un adaptador de transporte sin
dependencias externas. Se prueba con dobles offline y solo debe conectarse a un caso de
uso autorizado; no debe interpretar lenguaje natural ni ejecutar SQL directamente.
`TelegramCommandGateway` añade comandos estructurados, confirmación de venta, expiración
y rate limit por chat. `build_orchestrated_sale_executor` es el punto de integración con
`AIOrchestrator`; el worker de polling todavía se inicia fuera de FastAPI.

Para preparar una prueba de rol en una base local:

~~~powershell
uv run python -m backend.app.management correo@ejemplo.local MANAGER
~~~

### Pruebas de autenticación

Las pruebas de auth usan SQLite temporal y no requieren MySQL ni servicios externos. Antes
de entregar cambios ejecuta `uv run python -m pytest`; las contraseñas de prueba son datos
efímeros y nunca deben copiarse a `.env.local`.

## Flujo de una solicitud

1. Dash o CLI construye el proveedor y el repositorio seleccionados.
2. `SalesAgent` crea un `register_sale` vinculado a un UUID de solicitud.
3. El proveedor devuelve un tool call con el esquema `SaleCommand`.
4. Pydantic valida tipos, campos y moneda.
5. `SaleRecord.from_command` calcula precios y total.
6. `SalesRepository.append` verifica el UUID y escribe.
7. El modelo recibe el resultado de la herramienta y confirma la operación.
8. El dashboard lee los registros canónicos y recalcula métricas.

## Añadir un proveedor de IA

1. Agrega un valor a `Provider` y su `ProviderSpec`.
2. Implementa la construcción diferida en `build_chat_model`.
3. Añade su integración a `pyproject.toml`.
4. Documenta las variables sin incluir secretos.
5. Añade pruebas de configuración y manejo de errores.

El dominio y los repositorios no deben importar el SDK del proveedor.

## Añadir un repositorio

Implementa el protocolo `SalesRepository` con:

- `append(sale) -> bool`, conservando idempotencia por `transaction_id`.
- `list_all() -> list[SaleRecord]`.

Después amplía `build_repository`. No introduzcas dependencias del adaptador en el
dominio o en `SalesAgent`.

## Estrategia de pruebas

- Reglas de dinero y moneda: pruebas del dominio.
- Persistencia: archivos temporales o dobles controlados.
- Tool calling: `ToolCallingFakeModel`, sin consumo cloud.
- Proveedores reales: smoke tests manuales con cuentas de desarrollo.
- UI: inspección local y, cuando crezca, pruebas de flujos críticos con Playwright.

Las pruebas automáticas no deben depender de Internet, claves ni servicios pagados.

## Criterio para salir del MVP

Antes de incorporar una base de datos, cola o microservicios, registra evidencia de que
la solución actual falla por volumen, concurrencia, auditoría o disponibilidad. El cambio
debe implementarse detrás de los puertos existentes.

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

La primera migración solo establece el historial. Las tablas de negocio se añadirán junto
con los modelos de la siguiente fase.

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

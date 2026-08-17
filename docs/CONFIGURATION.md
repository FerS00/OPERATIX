# Configuración y seguridad

OPERATIX separa las credenciales de IA, las credenciales de Google y los datos
transaccionales. Ninguna clave debe quedar dentro del código o del historial de Git.

## Archivo local

Copia `.env.example` a `.env.local`. Este último está ignorado por Git.

```powershell
Copy-Item .env.example .env.local
```

No pegues valores reales en `.env.example`, capturas, issues o logs.

## Variables de proveedores de IA

| Variable | Obligatoria | Uso |
|---|---:|---|
| `OPENAI_API_KEY` | Solo para OpenAI | Clave de OpenAI Platform |
| `OPENAI_MODEL` | No | Modelo OpenAI seleccionado |
| `ANTHROPIC_API_KEY` | Solo para Anthropic | Clave de Anthropic Console |
| `ANTHROPIC_MODEL` | No | Modelo Anthropic seleccionado |
| `GOOGLE_API_KEY` | Solo para Gemini | Clave de Google AI Studio |
| `GOOGLE_MODEL` | No | Modelo Gemini seleccionado |

Solo es necesario configurar el proveedor que se vaya a usar. La interfaz permite
introducir una clave temporal, que se pasa al SDK durante el callback y no se persiste en
archivos ni en `dcc.Store`.

La clave temporal no constituye una solución multiusuario. Para desplegar OPERATIX se
debe usar un gestor de secretos y autenticación del usuario final; nunca enviar claves
del proveedor al navegador de clientes.

## Persistencia Excel heredada

| Variable | Valor predeterminado |
|---|---|
| `OPERATIX_STORAGE_BACKEND` | `excel` |
| `OPERATIX_EXCEL_PATH` | `data/operatix.xlsx` |

Los libros generados bajo `data/` están ignorados por Git porque pueden contener datos
de clientes.

## Archivos y reportes del backend

El backend usa MySQL para datos transaccionales y filesystem para el contenido binario.
La tabla `files` conserva metadata, hash SHA-256, propósito, usuario y ruta relativa; no
se guardan blobs Excel en MySQL.

| Variable | Valor predeterminado | Uso |
|---|---|---|
| `OPERATIX_STORAGE_ROOT` | `storage` | Raíz de `uploads/` y `exports/` |
| `OPERATIX_MAX_UPLOAD_BYTES` | `10485760` | Límite de cada archivo (10 MiB) |

Los endpoints aceptan `.xlsx`, `.csv` y `.tsv`. El nombre del usuario se conserva solo
como metadata; el nombre físico es un UUID generado por la aplicación. En producción,
respalda la carpeta configurada junto con MySQL y define una política de retención.

## Backend y MySQL

La API usa SQLAlchemy con el dialecto `mysql+pymysql`. En desarrollo local se puede usar
MySQL Community mediante `docker-compose.yml` sin contratar una base administrada.

| Variable | Valor predeterminado | Uso |
|---|---|---|
| `APP_NAME` | `OPERATIX API` | Nombre visible de la API |
| `APP_ENV` | `development` | Entorno de ejecución |
| `MYSQL_HOST` | `127.0.0.1` | Host de MySQL fuera de Docker |
| `MYSQL_PORT` | `3306` | Puerto de MySQL |
| `MYSQL_DATABASE` | `operatix` | Base de datos |
| `MYSQL_USER` | `operatix` | Usuario de aplicación |
| `MYSQL_PASSWORD` | — | Contraseña local, nunca se commitea |
| `MYSQL_ROOT_PASSWORD` | — | Contraseña local de Docker, nunca se commitea |
| `DATABASE_URL` | — | URL opcional que reemplaza las variables `MYSQL_*` |

`DATABASE_URL` y las contraseñas no deben aparecer en logs, capturas ni commits. Las
migraciones se ejecutan con `uv run alembic upgrade head` después de levantar MySQL.

## Dashboard y Telegram

| Variable | Valor predeterminado | Uso |
|---|---|---|
| `OPERATIX_FRONTEND_ORIGINS` | `http://localhost:5173,http://127.0.0.1:5173` | Orígenes CORS permitidos |
| `TELEGRAM_BOT_TOKEN` | — | Token opcional del bot; vacío deshabilita el adaptador |
| `TELEGRAM_POLL_INTERVAL_SECONDS` | `5` | Espera entre reintentos del polling local |

El frontend usa `VITE_API_URL` (por defecto `http://127.0.0.1:8000/api/v1`) y nunca
recibe secretos de proveedores LLM. Telegram usa long polling local; no se añadió un
webhook público ni hosting. El Bot API no exige pago por mensaje, pero el token debe
tratarse como secreto y cualquier hosting futuro tendría costo potencial.

En Compose, la API recibe automáticamente `JWT_SECRET`, la raíz persistente de archivos,
los orígenes CORS y las variables de Telegram. Cambiar `.env.local` requiere recrear el
servicio (`docker compose up -d --build`). Para una prueba local se puede asignar un rol
después del registro con `uv run python -m backend.app.management correo@ejemplo.local
MANAGER`; el helper está pensado para una base de desarrollo y no sustituye un flujo de
administración productivo.

## Autenticación

| Variable | Valor predeterminado | Uso |
|---|---|---|
| `JWT_SECRET` | — | Secreto de firma; mínimo 32 caracteres fuera de desarrollo |
| `JWT_ACCESS_TOKEN_EXPIRE_MINUTES` | `30` | Duración del access token |

Genera un secreto local con un gestor de contraseñas o `python -c "import secrets; print(secrets.token_urlsafe(32))"`.
No lo pegues en commits, issues ni logs.

## Persistencia Google Sheets

| Variable | Uso |
|---|---|
| `OPERATIX_STORAGE_BACKEND=google_sheets` | Activa el adaptador |
| `GOOGLE_SHEETS_SPREADSHEET_ID` | ID de la URL de la hoja |
| `GOOGLE_SHEETS_WORKSHEET` | Pestaña, por defecto `Ventas` |
| `GOOGLE_APPLICATION_CREDENTIALS` | JSON de la cuenta de servicio |

Procedimiento:

1. Crea un proyecto de desarrollo en Google Cloud.
2. Habilita Google Sheets API.
3. Crea una cuenta de servicio con el mínimo alcance necesario.
4. Guarda el JSON en `.secrets/google-service-account.json`.
5. Comparte la hoja con el correo `client_email` de la cuenta de servicio.
6. Configura el ID y ejecuta primero una operación de prueba sin datos reales.

El archivo `.gitignore` excluye `.secrets/`, patrones de cuentas de servicio y archivos
`.env` locales.

## LangSmith opcional

El trazado queda deshabilitado inicialmente. Cuando haya un dataset de evaluación,
configura `LANGSMITH_TRACING`, `LANGSMITH_API_KEY` y `LANGSMITH_PROJECT`. Revisa qué datos
se envían antes de habilitar trazas con información de clientes.

## Lista de seguridad antes de desplegar

- Reemplazar el servidor de desarrollo de Dash por un servidor WSGI apropiado.
- Almacenar secretos fuera del repositorio y del navegador.
- Autenticar usuarios y autorizar cada herramienta por rol.
- Añadir confirmación humana para operaciones sensibles.
- Validar origen y firma de webhooks.
- Añadir límites, reintentos controlados y registro sin datos sensibles.
- Definir retención, respaldo y eliminación de datos.

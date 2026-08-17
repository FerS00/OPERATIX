# Instalación, prueba y desinstalación en una PC de prueba

Esta guía deja OPERATIX funcionando en una computadora local y permite retirarlo sin
confundir una limpieza de la aplicación con una limpieza general de Docker. Está escrita
para Windows PowerShell y para una prueba sin servicios administrados.

## 1. Requisitos

Instala solamente herramientas locales y gratuitas:

- Python 3.12, 3.13 o 3.14.
- `uv` para el entorno Python.
- Node.js 20.19+ o 22.12+ y npm para el dashboard.
- Docker Desktop con Docker Compose v2 para la ruta recomendada.
- Git es opcional si recibes una copia comprimida del proyecto.

Comprueba las versiones:

```powershell
python --version
uv --version
node --version
npm --version
docker --version
docker compose version
```

Docker Desktop debe estar abierto antes de ejecutar los comandos de Compose. MySQL
Community se descarga como imagen local; no se usa PostgreSQL ni una base administrada.

## 2. Obtener el proyecto

Con Git:

```powershell
git clone https://github.com/FerS00/OPERATIX.git
Set-Location OPERATIX
```

Si se prueba la rama reconstruida local antes de publicarla, copia la carpeta completa
`OPERATIX` desde la máquina de desarrollo. No copies `.env.local`, `.venv`,
`frontend/node_modules`, `frontend/dist`, `storage/uploads` ni `storage/exports` si
contienen datos reales.

## 3. Crear configuración local

```powershell
Copy-Item .env.example .env.local
```

Edita `.env.local` y cambia como mínimo:

```dotenv
MYSQL_PASSWORD=una-clave-local
MYSQL_ROOT_PASSWORD=otra-clave-local
JWT_SECRET=un-secreto-aleatorio-de-al-menos-32-caracteres
```

Deja `TELEGRAM_BOT_TOKEN` vacío durante la primera prueba. Telegram es opcional y no
se necesita para probar el dashboard, la API, MySQL, archivos o reportes. Si se prueba
un bot real, crea el bot con BotFather y conserva el token únicamente en `.env.local`.

## 4. Instalar dependencias

Desde la raíz del repositorio:

```powershell
uv sync --dev
Push-Location frontend
npm install
Pop-Location
```

Las dependencias Python quedan en `.venv` y las de JavaScript en
`frontend/node_modules`; ambas rutas están ignoradas por Git.

## 5. Arranque recomendado con Docker

Este modo levanta MySQL Community y la API. La carpeta `storage` del proyecto se monta
en el contenedor para conservar uploads y exports durante una recreación del servicio.

```powershell
docker compose --env-file .env.local up -d --build
docker compose --env-file .env.local ps
```

Espera a que MySQL aparezca como `healthy`. Luego aplica las migraciones versionadas:

```powershell
docker compose --env-file .env.local exec api uv run alembic upgrade head
```

Verifica salud y disponibilidad:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/api/v1/health
Invoke-RestMethod http://127.0.0.1:8000/api/v1/health/ready
```

La respuesta de `health/ready` debe indicar que la base de datos está disponible. La API
queda en `http://127.0.0.1:8000`.

## 6. Arranque alternativo sin contenedor para la API

Usa esta ruta si la PC de prueba ya tiene un MySQL local en `127.0.0.1:3306` y deseas
evitar Docker. Ajusta `MYSQL_*` en `.env.local`, crea la base y ejecuta:

```powershell
uv run alembic upgrade head
uv run uvicorn backend.app.main:app --reload
```

No ejecutes simultáneamente el MySQL de Compose y otro MySQL usando el mismo puerto.

## 7. Arrancar el dashboard React

En otra ventana de PowerShell:

```powershell
Set-Location frontend
npm run dev
```

Abre `http://localhost:5173`. El frontend usa por defecto
`http://127.0.0.1:8000/api/v1`. Para una API en otra dirección crea
`frontend/.env.local` con:

```dotenv
VITE_API_URL=http://127.0.0.1:8000/api/v1
```

## 8. Prueba funcional mínima

1. Registra un usuario desde la pantalla de acceso.
2. Comprueba que puede consultar sus datos y que inicialmente tiene rol `USER`.
3. Con la API autenticada, crea un cliente y un producto; la pantalla
   **Clientes y productos** debe mostrarlos.
4. Carga un `.xlsx`, `.csv` o `.tsv` de prueba y verifica la vista previa y descarga.
5. Promueve el usuario únicamente en la PC de prueba si necesitas probar operaciones de
   administración:

   ```powershell
   docker compose --env-file .env.local exec api uv run python -m backend.app.management correo@prueba.local MANAGER
   ```

   Cierra sesión y vuelve a entrar para recibir el nuevo rol. El registro público nunca
   asigna `ADMIN` o `MANAGER` por sí solo.
6. Crea una venta con una clave `Idempotency-Key`; repítela con los mismos datos y
   confirma que no duplica la venta. Reutilizar la clave con otros datos debe fallar.
7. Si el usuario tiene permiso, genera el reporte y verifica que USD, PEN y otras monedas
   aparecen separadas.

No uses datos personales ni archivos de producción en esta prueba.

## 9. Prueba opcional de Telegram

Configura `TELEGRAM_BOT_TOKEN` en `.env.local`, recrea la API y conecta el adaptador desde
un proceso local que invoque `TelegramChannel.poll` y `TelegramCommandGateway`. Los
comandos estructurados son:

```text
/ayuda
/venta <cliente_id> <producto_id> <cantidad> [clave]
/confirmar <código>
/cancelar <código>
```

Una venta nunca se ejecuta al recibir `/venta`: primero se devuelve un código y se exige
`/confirmar`. La confirmación queda vinculada al mismo chat, expira y el gateway limita
solicitudes por chat. El repositorio todavía no inicia un worker de Telegram de forma
automática; esta integración queda para una siguiente fase de operación.

## 10. Validaciones antes de entregar la PC

Desde la raíz:

```powershell
uv run ruff check .
uv run ruff format --check .
uv run python -m pytest
semgrep scan --config p/python --config p/security-audit backend src tests
Push-Location frontend
npm run build
Pop-Location
```

Estas comprobaciones son locales y no consumen APIs de pago. Las pruebas automáticas no
requieren claves LLM, Telegram ni una cuenta de Google.

## 11. Detener y desinstalar

Para detener la instalación sin borrar datos de prueba:

```powershell
docker compose --env-file .env.local down
```

Para eliminar también la base de datos y el volumen de MySQL **solo en la PC de prueba**:

```powershell
docker compose --env-file .env.local down -v
```

Después puedes retirar de forma manual, revisando antes que no contengan datos que quieras
conservar:

```powershell
Remove-Item -Recurse -Force frontend\node_modules, frontend\dist, .venv
Remove-Item -Force .env.local
```

Borra `storage\uploads` y `storage\exports` únicamente si deseas eliminar los archivos
de prueba. No ejecutes `docker system prune` para desinstalar OPERATIX: también puede
eliminar imágenes, volúmenes o cachés de otros proyectos.

Finalmente, elimina la carpeta del repositorio desde el Explorador de archivos. Si se
conserva para otra prueba, deja `.env.example`, `README.md` y esta guía, pero crea un
`.env.local` nuevo con secretos nuevos.

## 12. Problemas frecuentes

- **La API no arranca:** revisa que `JWT_SECRET` tenga al menos 32 caracteres y que
  `MYSQL_PASSWORD`/`MYSQL_ROOT_PASSWORD` no estén vacíos.
- **`health/ready` falla:** espera a que el contenedor MySQL esté `healthy` y vuelve a
  ejecutar la migración.
- **El dashboard muestra error CORS:** confirma que el origen del navegador esté incluido
  en `OPERATIX_FRONTEND_ORIGINS` y recrea el servicio `api`.
- **Puerto ocupado:** cambia `MYSQL_PORT`, `API_PORT` o el puerto del frontend y ajusta
  `VITE_API_URL` si corresponde.
- **No permite exportar o administrar:** el registro crea `USER`; asigna `MANAGER` o
  `ADMIN` con el helper local y vuelve a iniciar sesión.
- **La descarga falla:** usa el dashboard autenticado; los archivos requieren el header
  JWT y no aceptan tokens en la URL.

## Costos

La instalación descrita usa Python, uv, Node.js, Docker Desktop, MySQL Community y
Telegram long polling sin contratar hosting ni base administrada. No se añade ningún
costo obligatorio. Pueden aparecer costos únicamente si se activan proveedores LLM,
Google Sheets, hosting, almacenamiento externo o un dominio; deben decidirse por separado.


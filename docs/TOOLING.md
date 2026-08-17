# MCP, plugins y CLI recomendados

Las herramientas de desarrollo no forman parte del runtime de OPERATIX. El producto usa
las APIs de los proveedores; Codex y OpenCode usan MCP/plugins para ayudarte a construirlo.

## Instalar o habilitar ahora

1. **Context7 MCP en OpenCode:** documentación actual de LangChain, Dash, gspread y SDKs.
   En Codex ya está disponible.
2. **GitHub MCP oficial en OpenCode:** repositorio, issues, PR y CI con alcance controlado.
   Codex ya tiene la integración de GitHub.
3. **GitHub CLI (`gh`):** falta en este equipo. Simplifica autenticación, clonado, ramas,
   PR y revisión de CI desde la terminal.
4. **`uv`, Ruff y pytest:** `uv` ya está instalado; Ruff y pytest quedan fijados como
   dependencias de desarrollo y se ejecutan mediante `uv run`.

## Añadir en la segunda iteración

- **LangSmith MCP y tracing:** útil cuando existan prompts estables y un pequeño dataset
  de evaluación. Antes de eso añade configuración y coste sin suficiente señal.
- **MCP Inspector:** imprescindible si OPERATIX expone sus herramientas como un servidor
  MCP para otras aplicaciones.
- **Google Cloud CLI (`gcloud`):** ayuda a administrar proyecto, APIs y cuentas de servicio
  de Google Sheets; no reemplaza las credenciales de runtime.
- **Sentry para Codex y el SDK de Sentry en el proyecto:** al desplegar el webhook o Dash.
- **Cloudflare/cloudflared:** para exponer temporalmente un webhook local o desplegar el
  borde. No se necesita para el Paso 1 local.

## Posponer por YAGNI

- PostHog hasta que haya usuarios reales y preguntas de producto.
- Slack, Teams o WhatsApp hasta elegir el primer canal de entrada.
- Supabase, Neon o cualquier Postgres mientras Excel/Sheets satisfaga volumen y
  concurrencia.
- Docker y Kubernetes hasta que haya un destino de despliegue concreto.
- Un MCP de Google Sheets dentro de OPERATIX: el runtime debe usar la API directamente;
  el MCP es una ayuda para los agentes de desarrollo, no una dependencia transaccional.

## Configuración de OpenCode

OpenCode admite servidores locales o remotos bajo `mcp.servers`. Mantén habilitados solo
los necesarios porque cada servidor aumenta el contexto y la superficie de permisos.
Usa referencias a variables de entorno para tokens; nunca pegues secretos en el JSON.

Enlaces oficiales:

- https://opencode.ai/v2/docs/mcp-servers
- https://github.com/github/github-mcp-server
- https://github.com/modelcontextprotocol/inspector
- https://docs.langchain.com/langsmith/langsmith-mcp-server
- https://docs.astral.sh/uv/
- https://docs.astral.sh/ruff/
- https://cli.github.com/manual/

# OPERATIX agent instructions

- Keep the MVP modular and apply YAGNI: domain/application code must not depend on Dash,
  Excel, Google Sheets, or a specific LLM provider.
- Use `uv` for dependency management and execution.
- Run `uv run ruff check .`, `uv run ruff format --check .`, and `uv run pytest`
  before handing off changes.
- Never commit API keys, OAuth tokens, service-account JSON files, customer data,
  generated workbooks, or `.env.local`.
- Treat tool calls that write transactions as side effects. Preserve transaction IDs
  and idempotency checks when changing persistence adapters.
- Keep provider model names configurable because cloud model availability changes.

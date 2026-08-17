# Alembic migrations

The database engine is MySQL through SQLAlchemy. This initial migration establishes the
history; business tables will be added with the domain phase.

Run from the repository root after configuring `.env.local`:

```powershell
uv run alembic upgrade head
```

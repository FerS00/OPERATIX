# Alembic migrations

The database engine is MySQL through SQLAlchemy. The security migration adds users, roles,
permissions and audit logs; business tables will be added with the domain phase.

Run from the repository root after configuring `.env.local`:

```powershell
uv run alembic upgrade head
```

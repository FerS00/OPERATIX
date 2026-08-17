# Alembic migrations

The database engine is MySQL through SQLAlchemy. The security migration adds users, roles,
permissions and audit logs; migration `0003_business` adds customers, products, inventory
and sales.

Run from the repository root after configuring `.env.local`:

```powershell
uv run alembic upgrade head
```

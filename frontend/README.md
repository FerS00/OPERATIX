# OPERATIX frontend

Dashboard React + TypeScript + Tailwind + Recharts para la API FastAPI local.

```powershell
npm install
npm run dev
```

Configura `VITE_API_URL` si la API no está en `http://127.0.0.1:8000/api/v1`.
El dashboard no guarda credenciales de proveedores LLM; solo conserva temporalmente el
JWT de sesión en `sessionStorage` para el MVP local.

import { useCallback, useEffect, useMemo, useState } from "react";
import type { ChangeEvent, FormEvent, ReactNode } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { ApiError, api, downloadFile } from "./api";
import type { AuditEntry, Customer, Inventory, Product, Sale, SalesSummary, StoredFile, User } from "./api";

const TOKEN_KEY = "operatix.access_token";

type ChartPoint = { currency: string; total: number; transactions: number };

function App() {
  const [token, setToken] = useState(() => sessionStorage.getItem(TOKEN_KEY));
  const [user, setUser] = useState<User | null>(null);
  const [sales, setSales] = useState<Sale[]>([]);
  const [customers, setCustomers] = useState<Customer[]>([]);
  const [products, setProducts] = useState<Product[]>([]);
  const [inventory, setInventory] = useState<Inventory[]>([]);
  const [files, setFiles] = useState<StoredFile[]>([]);
  const [summary, setSummary] = useState<SalesSummary | null>(null);
  const [audit, setAudit] = useState<AuditEntry[]>([]);
  const [loading, setLoading] = useState(false);
  const [notice, setNotice] = useState("");
  const [error, setError] = useState("");

  const signOut = useCallback(() => {
    sessionStorage.removeItem(TOKEN_KEY);
    setToken(null);
    setUser(null);
  }, []);

  const loadDashboard = useCallback(
    async (activeToken: string) => {
      setLoading(true);
      setError("");
      try {
        const [currentUser, currentSales, currentCustomers, currentProducts, currentInventory, currentFiles] = await Promise.all([
          api.me(activeToken),
          api.sales(activeToken),
          api.customers(activeToken),
          api.products(activeToken),
          api.inventory(activeToken),
          api.files(activeToken),
        ]);
        setUser(currentUser);
        setSales(currentSales);
        setCustomers(currentCustomers);
        setProducts(currentProducts);
        setInventory(currentInventory);
        setFiles(currentFiles);
        if (currentUser.roles.includes("ADMIN")) {
          setAudit(await api.audit(activeToken));
        } else {
          setAudit([]);
        }
        try {
          setSummary(await api.summary(activeToken));
        } catch (summaryError) {
          if (!(summaryError instanceof ApiError && summaryError.status === 403)) throw summaryError;
          setSummary(null);
        }
      } catch (loadError) {
        if (loadError instanceof ApiError && loadError.status === 401) signOut();
        setError(loadError instanceof Error ? loadError.message : "No se pudo cargar el panel");
      } finally {
        setLoading(false);
      }
    },
    [signOut],
  );

  useEffect(() => {
    if (token) void loadDashboard(token);
  }, [loadDashboard, token]);

  if (!token) {
    return (
      <Login
        onAuthenticated={(nextToken) => {
          sessionStorage.setItem(TOKEN_KEY, nextToken);
          setToken(nextToken);
        }}
      />
    );
  }

  const canExport = user?.roles.some((role) => role === "ADMIN" || role === "MANAGER") ?? false;
  return (
    <div className="min-h-screen bg-[#f5f7fb] text-slate-900">
      <header className="border-b border-slate-200 bg-white/90 px-5 py-4 backdrop-blur md:px-10">
        <div className="mx-auto flex max-w-7xl items-center justify-between">
          <Brand />
          <div className="flex items-center gap-4 text-right">
            <div className="hidden sm:block">
              <p className="text-sm font-medium">{user?.email}</p>
              <p className="text-xs text-slate-500">{user?.roles.join(" · ")}</p>
            </div>
            <button onClick={signOut} className="button-secondary">Salir</button>
          </div>
        </div>
      </header>

      <main className="mx-auto grid max-w-7xl gap-6 px-5 py-7 md:px-10 lg:grid-cols-[220px_1fr]">
        <aside className="hidden lg:block">
          <p className="mb-3 text-xs font-semibold uppercase tracking-wider text-slate-400">Navegación</p>
          <nav className="space-y-1 text-sm">
            <a className="nav-item nav-active" href="#resumen">Resumen</a>
            <a className="nav-item" href="#ventas">Ventas</a>
            <a className="nav-item" href="#maestros">Clientes y productos</a>
            <a className="nav-item" href="#inventario">Inventario</a>
            <a className="nav-item" href="#archivos">Archivos</a>
            <a className="nav-item" href="#reportes">Reportes</a>
            {user?.roles.includes("ADMIN") && <a className="nav-item" href="#auditoria">Auditoría</a>}
          </nav>
        </aside>

        <section className="min-w-0 space-y-6">
          <div className="flex flex-wrap items-end justify-between gap-3">
            <div>
              <p className="text-sm font-medium text-[#1f7a8c]">Vista general</p>
              <h1 className="mt-1 text-3xl font-bold tracking-tight text-[#173f5f]">Tu operación, en contexto</h1>
              <p className="mt-2 text-sm text-slate-500">Datos de MySQL y archivos locales, listos para decidir.</p>
            </div>
            <button
              onClick={() => void loadDashboard(token)}
              className="button-primary"
              disabled={loading}
            >
              {loading ? "Actualizando…" : "Actualizar"}
            </button>
          </div>

          {error && <div className="alert-error">{error}</div>}
          {notice && <div className="alert-success">{notice}</div>}
          <Kpis sales={sales} inventory={inventory} summary={summary} />

          <div id="maestros" className="grid gap-6 xl:grid-cols-2">
            <MasterDataCard title="Clientes" items={customers.map((customer) => ({ id: customer.id, title: customer.name, detail: customer.email ?? "Sin correo" }))} empty="No hay clientes registrados." />
            <MasterDataCard title="Productos" items={products.map((product) => ({ id: product.id, title: product.name, detail: `${product.sku} · ${product.unit_price} ${product.currency}` }))} empty="No hay productos registrados." />
          </div>

          <div id="resumen" className="grid gap-6 xl:grid-cols-[1.2fr_0.8fr]">
            <SalesChart sales={sales} summary={summary} />
            <InventoryCard inventory={inventory} />
          </div>

          <div id="ventas" className="card">
            <SectionHeading eyebrow="Actividad" title="Ventas recientes" action={`${sales.length} registros`} />
            <SalesTable sales={sales} />
          </div>

          <div id="archivos" className="grid gap-6 xl:grid-cols-[1fr_0.8fr]">
              <FilesCard
              files={files}
              token={token}
              onUploaded={(file) => {
                setFiles((current) => [file, ...current]);
                setNotice(`Archivo ${file.original_name} almacenado correctamente.`);
              }}
              onError={setError}
            />
            <ReportsCard
              canExport={canExport}
              token={token}
              onExport={(file) => {
                setFiles((current) => [file, ...current]);
                setNotice(`Reporte ${file.original_name} generado.`);
              }}
              onError={setError}
            />
          </div>

          <div id="reportes" className="rounded-xl bg-[#173f5f] px-5 py-4 text-sm text-slate-200">
            <span className="font-semibold text-white">Control de datos:</span> los totales del panel no mezclan monedas;
            las exportaciones se guardan fuera de MySQL y quedan auditadas.
          </div>
          {user?.roles.includes("ADMIN") && <AuditCard entries={audit} />}
        </section>
      </main>
    </div>
  );
}

function Brand() {
  return (
    <div className="flex items-center gap-3">
      <div className="grid size-10 place-items-center rounded-xl bg-[#173f5f] text-lg font-bold text-white">O</div>
      <div>
        <p className="text-sm font-semibold tracking-[0.2em] text-[#173f5f]">OPERATIX</p>
        <p className="text-xs text-slate-500">Centro operativo</p>
      </div>
    </div>
  );
}

function Login({ onAuthenticated }: { onAuthenticated: (token: string) => void }) {
  const [mode, setMode] = useState<"login" | "register">("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setLoading(true);
    setError("");
    try {
      if (mode === "register") await api.register(email, password);
      const response = await api.login(email, password);
      onAuthenticated(response.access_token);
    } catch (submitError) {
      setError(submitError instanceof Error ? submitError.message : "No se pudo iniciar sesión");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="grid min-h-screen place-items-center bg-[#173f5f] px-5">
      <div className="w-full max-w-md rounded-3xl bg-white p-8 shadow-2xl">
        <div className="mb-8">
          <div className="mb-6 grid size-12 place-items-center rounded-2xl bg-[#1f7a8c] text-xl font-bold text-white">O</div>
          <p className="text-sm font-semibold tracking-[0.25em] text-[#1f7a8c]">OPERATIX</p>
          <h1 className="mt-2 text-3xl font-bold text-[#173f5f]">{mode === "login" ? "Bienvenido" : "Crea tu acceso"}</h1>
          <p className="mt-2 text-sm text-slate-500">Panel operativo local con FastAPI y MySQL.</p>
        </div>
        {error && <div className="alert-error mb-4">{error}</div>}
        <form className="space-y-4" onSubmit={submit}>
          <label className="field-label">Correo<input className="field-input" type="email" value={email} onChange={(event) => setEmail(event.target.value)} required /></label>
          <label className="field-label">Contraseña<input className="field-input" type="password" minLength={8} value={password} onChange={(event) => setPassword(event.target.value)} required /></label>
          <button className="button-primary w-full justify-center" disabled={loading}>{loading ? "Procesando…" : mode === "login" ? "Iniciar sesión" : "Registrarme"}</button>
        </form>
        <button className="mt-5 w-full text-sm font-medium text-[#1f7a8c]" onClick={() => setMode(mode === "login" ? "register" : "login")}>
          {mode === "login" ? "Crear una cuenta" : "Ya tengo una cuenta"}
        </button>
      </div>
    </div>
  );
}

function Kpis({ sales, inventory, summary }: { sales: Sale[]; inventory: Inventory[]; summary: SalesSummary | null }) {
  const transactions = summary?.transactions ?? sales.length;
  const units = summary?.units ?? sales.reduce((total, sale) => total + sale.quantity, 0);
  const stock = inventory.reduce((total, item) => total + item.quantity, 0);
  const currencies = Object.keys(summary?.by_currency ?? aggregateSales(sales));
  const cards = [
    ["Transacciones", transactions.toString(), "ventas registradas"],
    ["Unidades", units.toString(), "unidades vendidas"],
    ["Stock disponible", stock.toString(), "unidades en inventario"],
    ["Monedas activas", currencies.length.toString(), currencies.join(" · ") || "sin datos"],
  ];
  return <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">{cards.map(([label, value, helper]) => <div className="card" key={label}><p className="text-sm text-slate-500">{label}</p><p className="mt-3 text-3xl font-bold tracking-tight text-[#173f5f]">{value}</p><p className="mt-2 text-xs text-slate-400">{helper}</p></div>)}</div>;
}

function SalesChart({ sales, summary }: { sales: Sale[]; summary: SalesSummary | null }) {
  const chart = useMemo<ChartPoint[]>(
    () => Object.entries(summary?.by_currency ?? aggregateSales(sales)).map(([currency, values]) => ({ currency, total: Number(values.total), transactions: values.transactions })),
    [sales, summary],
  );
  return <div className="card"><SectionHeading eyebrow="Rendimiento" title="Importe por moneda" action="sin conversiones" /><div className="mt-6 h-64">{chart.length ? <ResponsiveContainer width="100%" height="100%"><BarChart data={chart} margin={{ top: 5, right: 5, bottom: 0, left: -20 }}><CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e2e8f0" /><XAxis dataKey="currency" axisLine={false} tickLine={false} tick={{ fill: "#64748b", fontSize: 12 }} /><YAxis axisLine={false} tickLine={false} tick={{ fill: "#64748b", fontSize: 12 }} /><Tooltip formatter={(value) => [`${value}`, "Total"]} /><Bar dataKey="total" fill="#1f7a8c" radius={[6, 6, 0, 0]} /></BarChart></ResponsiveContainer> : <EmptyState message="Aún no hay ventas para graficar." />}</div></div>;
}

function InventoryCard({ inventory }: { inventory: Inventory[] }) {
  return <div id="inventario" className="card"><SectionHeading eyebrow="Existencias" title="Inventario" action={`${inventory.length} productos`} /><div className="mt-5 space-y-3">{inventory.slice(0, 6).map((item) => <div className="flex items-center justify-between border-b border-slate-100 pb-3 text-sm" key={item.product_id}><span className="truncate pr-3 font-medium text-slate-700">{item.product_id.slice(0, 12)}…</span><span className={item.quantity < 5 ? "badge-warning" : "badge-success"}>{item.quantity} unidades</span></div>)}{!inventory.length && <EmptyState message="No hay inventario registrado." />}</div></div>;
}

function MasterDataCard({ title, items, empty }: { title: string; items: { id: string; title: string; detail: string }[]; empty: string }) {
  return <div className="card"><SectionHeading eyebrow="Datos maestros" title={title} action={`${items.length} registros`} /><div className="mt-5 space-y-3">{items.slice(0, 6).map((item) => <div className="flex items-center justify-between gap-3 border-b border-slate-100 pb-3 text-sm" key={item.id}><span className="truncate font-medium text-slate-700">{item.title}</span><span className="truncate text-right text-xs text-slate-400">{item.detail}</span></div>)}{!items.length && <EmptyState message={empty} />}</div></div>;
}

function SalesTable({ sales }: { sales: Sale[] }) {
  return sales.length ? <div className="mt-4 overflow-x-auto"><table className="w-full min-w-[650px] text-left text-sm"><thead className="border-b border-slate-100 text-xs uppercase tracking-wider text-slate-400"><tr><th className="px-3 py-3">Venta</th><th className="px-3 py-3">Cliente</th><th className="px-3 py-3">Cantidad</th><th className="px-3 py-3">Total</th><th className="px-3 py-3">Moneda</th></tr></thead><tbody>{sales.slice(0, 8).map((sale) => <tr className="border-b border-slate-50" key={sale.id}><td className="px-3 py-3 font-mono text-xs text-slate-500">{sale.id.slice(0, 10)}…</td><td className="px-3 py-3 text-slate-600">{sale.customer_id.slice(0, 10)}…</td><td className="px-3 py-3 text-slate-600">{sale.quantity}</td><td className="px-3 py-3 font-semibold text-[#173f5f]">{sale.total_amount}</td><td className="px-3 py-3"><span className="badge-neutral">{sale.currency}</span></td></tr>)}</tbody></table></div> : <EmptyState message="Las ventas aparecerán aquí cuando se registre la primera operación." />;
}

function FilesCard({ files, token, onUploaded, onError }: { files: StoredFile[]; token: string; onUploaded: (file: StoredFile) => void; onError: (message: string) => void }) {
  const [uploading, setUploading] = useState(false);
  async function upload(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    if (!file) return;
    setUploading(true);
    try { onUploaded(await api.upload(token, file)); } catch (uploadError) { onError(uploadError instanceof Error ? uploadError.message : "No se pudo cargar el archivo"); } finally { setUploading(false); event.target.value = ""; }
  }
  async function download(file: StoredFile) {
    try { await downloadFile(token, file.id, file.original_name); } catch (downloadError) { onError(downloadError instanceof Error ? downloadError.message : "No se pudo descargar el archivo"); }
  }
  return <div className="card"><SectionHeading eyebrow="Documentos" title="Archivos" action={<label className="button-soft">{uploading ? "Cargando…" : "Subir archivo"}<input className="hidden" type="file" accept=".xlsx,.csv,.tsv" onChange={upload} disabled={uploading} /></label>} /><div className="mt-5 space-y-3">{files.slice(0, 5).map((file) => <button className="flex w-full items-center justify-between rounded-lg bg-slate-50 px-3 py-3 text-left text-sm transition hover:bg-slate-100" onClick={() => void download(file)} key={file.id}><span className="truncate pr-3 font-medium text-slate-600">{file.original_name}</span><span className="text-xs text-slate-400">{formatBytes(file.size_bytes)}</span></button>)}{!files.length && <EmptyState message="No hay archivos registrados." />}</div></div>;
}

function ReportsCard({ canExport, token, onExport, onError }: { canExport: boolean; token: string; onExport: (file: StoredFile) => void; onError: (message: string) => void }) {
  const [exporting, setExporting] = useState(false);
  async function exportReport() {
    setExporting(true);
    try { onExport(await api.exportReport(token)); } catch (exportError) { onError(exportError instanceof Error ? exportError.message : "No se pudo exportar el reporte"); } finally { setExporting(false); }
  }
  return <div className="card"><SectionHeading eyebrow="Salida" title="Reportes" action={canExport ? <button onClick={() => void exportReport()} className="button-primary compact" disabled={exporting}>{exporting ? "Generando…" : "Exportar Excel"}</button> : <span className="text-xs text-slate-400">Permiso EXPORT requerido</span>} /><p className="mt-5 text-sm leading-6 text-slate-500">Los reportes se agregan por moneda y generan un libro sin fórmulas. El archivo queda auditado y disponible en la sección de documentos.</p></div>;
}

function AuditCard({ entries }: { entries: AuditEntry[] }) {
  return <div id="auditoria" className="card"><SectionHeading eyebrow="Trazabilidad" title="Auditoría reciente" action={`${entries.length} eventos`} /><div className="mt-5 space-y-2">{entries.slice(0, 6).map((entry) => <div className="flex flex-wrap items-center justify-between gap-2 rounded-lg bg-slate-50 px-3 py-3 text-sm" key={entry.id}><div><p className="font-semibold text-slate-700">{entry.action}</p><p className="text-xs text-slate-400">{entry.tool ?? "sistema"} · {entry.parameters_summary || "sin parámetros"}</p></div><span className={entry.status === "success" ? "badge-success" : "badge-warning"}>{entry.status}</span></div>)}{!entries.length && <EmptyState message="No hay eventos de auditoría visibles para este rol." />}</div></div>;
}

function SectionHeading({ eyebrow, title, action }: { eyebrow: string; title: string; action?: ReactNode }) {
  return <div className="flex items-end justify-between gap-3"><div><p className="text-xs font-semibold uppercase tracking-[0.18em] text-[#1f7a8c]">{eyebrow}</p><h2 className="mt-1 text-lg font-bold text-[#173f5f]">{title}</h2></div>{action && <div>{action}</div>}</div>;
}

function EmptyState({ message }: { message: string }) { return <div className="grid min-h-24 place-items-center rounded-xl border border-dashed border-slate-200 px-4 text-center text-sm text-slate-400">{message}</div>; }

function aggregateSales(sales: Sale[]): Record<string, { transactions: number; units: number; total: string }> {
  return sales.reduce<Record<string, { transactions: number; units: number; total: string }>>((result, sale) => {
    const current = result[sale.currency] ?? { transactions: 0, units: 0, total: "0" };
    current.transactions += 1;
    current.units += sale.quantity;
    current.total = (Number(current.total) + Number(sale.total_amount)).toFixed(2);
    result[sale.currency] = current;
    return result;
  }, {});
}

function formatBytes(bytes: number) {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export default App;

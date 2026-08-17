export type User = { id: string; email: string; is_active: boolean; roles: string[] };
export type Sale = {
  id: string;
  customer_id: string;
  product_id: string;
  quantity: number;
  unit_price: string;
  total_amount: string;
  currency: string;
  notes: string | null;
  created_by: string;
};
export type Inventory = { product_id: string; quantity: number };
export type StoredFile = {
  id: string;
  original_name: string;
  mime_type: string;
  size_bytes: number;
  sha256: string;
  purpose: string;
  created_by: string;
  created_at: string;
};
export type SalesSummary = {
  transactions: number;
  units: number;
  by_currency: Record<string, { transactions: number; units: number; total: string }>;
};
export type AuditEntry = {
  id: string;
  action: string;
  tool: string | null;
  parameters_summary: string;
  result: string;
  status: string;
  created_at: string;
};

const API_URL = (import.meta.env.VITE_API_URL ?? "http://127.0.0.1:8000/api/v1").replace(/\/$/, "");

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

async function request<T>(path: string, options: RequestInit = {}, token?: string): Promise<T> {
  const headers = new Headers(options.headers);
  if (options.body && !(options.body instanceof FormData)) headers.set("Content-Type", "application/json");
  if (token) headers.set("Authorization", `Bearer ${token}`);
  const response = await fetch(`${API_URL}${path}`, { ...options, headers });
  if (!response.ok) {
    const payload = await response.json().catch(() => ({}));
    const detail = typeof payload.detail === "string" ? payload.detail : `Error HTTP ${response.status}`;
    throw new ApiError(response.status, detail);
  }
  if (response.status === 204) return undefined as T;
  return response.json() as Promise<T>;
}

export const api = {
  login: (email: string, password: string) =>
    request<{ access_token: string; token_type: string }>("/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    }),
  register: (email: string, password: string) =>
    request<User>("/auth/register", { method: "POST", body: JSON.stringify({ email, password }) }),
  me: (token: string) => request<User>("/auth/me", {}, token),
  sales: (token: string) => request<Sale[]>("/sales", {}, token),
  inventory: (token: string) => request<Inventory[]>("/inventory", {}, token),
  files: (token: string) => request<StoredFile[]>("/files", {}, token),
  summary: (token: string) => request<SalesSummary>("/reports/sales/summary", {}, token),
  audit: (token: string) => request<AuditEntry[]>("/security/audit", {}, token),
  upload: (token: string, file: File) => {
    const body = new FormData();
    body.append("upload", file);
    return request<StoredFile>("/files/upload", { method: "POST", body }, token);
  },
  exportReport: (token: string) =>
    request<StoredFile>("/reports/sales/export", { method: "POST" }, token),
};

export function fileDownloadUrl(fileId: string): string {
  return `${API_URL}/files/${fileId}/download`;
}

export async function downloadFile(token: string, fileId: string, filename: string): Promise<void> {
  const response = await fetch(fileDownloadUrl(fileId), {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!response.ok) throw new ApiError(response.status, "No se pudo descargar el archivo");
  const objectUrl = URL.createObjectURL(await response.blob());
  const link = document.createElement("a");
  link.href = objectUrl;
  link.download = filename;
  link.click();
  URL.revokeObjectURL(objectUrl);
}

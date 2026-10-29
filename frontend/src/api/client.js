const API_ROOT = import.meta.env.VITE_API_ROOT || "http://localhost:8000/api";

export async function request(token, path, options = {}) {
  const headers = new Headers(options.headers || {});
  headers.set("Authorization", `Bearer ${token}`);
  if (options.body && !(options.body instanceof FormData)) {
    headers.set("Content-Type", "application/json");
  }
  const response = await fetch(`${API_ROOT}${path}`, { ...options, headers });
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    const detail = typeof body.detail === "string" ? body.detail : body.detail?.message;
    throw new Error(detail || `Request failed (${response.status})`);
  }
  if (response.headers.get("content-type")?.includes("text/csv")) {
    return response.blob();
  }
  return response.json();
}
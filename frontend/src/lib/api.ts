const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem("hf_access_token");
}

export function setTokens(access: string, refresh: string) {
  localStorage.setItem("hf_access_token", access);
  localStorage.setItem("hf_refresh_token", refresh);
}

export function clearTokens() {
  localStorage.removeItem("hf_access_token");
  localStorage.removeItem("hf_refresh_token");
  localStorage.removeItem("hf_user");
}

export function setUser(user: object) {
  localStorage.setItem("hf_user", JSON.stringify(user));
}

export function getUser(): Record<string, string> | null {
  if (typeof window === "undefined") return null;
  const raw = localStorage.getItem("hf_user");
  return raw ? JSON.parse(raw) : null;
}

export async function api<T>(
  path: string,
  options: RequestInit = {}
): Promise<T> {
  const token = getToken();
  const headers: Record<string, string> = {
    ...(options.headers as Record<string, string>),
  };
  if (!(options.body instanceof FormData)) {
    headers["Content-Type"] = headers["Content-Type"] || "application/json";
  }
  if (token) headers.Authorization = `Bearer ${token}`;

  const res = await fetch(`${API_URL}${path}`, { ...options, headers });
  const data = await res.json().catch(() => ({}));

  if (!res.ok) {
    throw new Error(data.detail || data.message || "Request failed");
  }
  return data as T;
}

export { API_URL };

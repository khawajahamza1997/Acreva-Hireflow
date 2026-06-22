/** Production Render API — used when NEXT_PUBLIC_API_URL is missing on Vercel */
const PRODUCTION_API = "https://hireflow-api-dx5u.onrender.com";

export function getApiBaseUrl(): string {
  const fromEnv = process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, "");
  if (fromEnv) return fromEnv;

  if (typeof window !== "undefined" && window.location.hostname.includes("vercel.app")) {
    return PRODUCTION_API;
  }

  return "http://localhost:8000";
}

function formatFetchError(err: unknown, apiUrl: string): string {
  const msg = err instanceof Error ? err.message : "Network error";
  if (msg.includes("Failed to fetch") || msg.includes("NetworkError")) {
    if (apiUrl.includes("localhost")) {
      return (
        "Cannot reach API. Set NEXT_PUBLIC_API_URL on Vercel to " +
        PRODUCTION_API + " and redeploy."
      );
    }
    return (
      "Cannot reach API — Render may be waking up (wait 60s and retry). " +
      `Trying: ${apiUrl}`
    );
  }
  return msg;
}

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
  const apiUrl = getApiBaseUrl();
  const token = getToken();
  const headers: Record<string, string> = {
    ...(options.headers as Record<string, string>),
  };
  if (!(options.body instanceof FormData)) {
    headers["Content-Type"] = headers["Content-Type"] || "application/json";
  }
  if (token) headers.Authorization = `Bearer ${token}`;

  let res: Response;
  try {
    res = await fetch(`${apiUrl}${path}`, { ...options, headers });
  } catch (err) {
    throw new Error(formatFetchError(err, apiUrl));
  }
  const data = await res.json().catch(() => ({}));

  if (!res.ok) {
    const detail = data.detail;
    const message =
      typeof detail === "string"
        ? detail
        : Array.isArray(detail)
          ? detail.map((d: { msg?: string }) => d.msg).join(", ")
          : data.message || "Request failed";
    throw new Error(message);
  }
  return data as T;
}

export const API_URL = getApiBaseUrl();

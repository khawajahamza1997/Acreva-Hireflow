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

const sleep = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms));

/** Ping Render so it wakes before signup/login (free tier sleeps when idle). */
export async function wakeApi(): Promise<boolean> {
  const apiUrl = getApiBaseUrl();
  if (apiUrl.includes("localhost")) return true;

  for (let attempt = 0; attempt < 3; attempt++) {
    try {
      const res = await fetch(`${apiUrl}/health`, { cache: "no-store" });
      if (res.ok) return true;
    } catch {
      /* Render still starting */
    }
    await sleep(8000);
  }
  return false;
}

function formatFetchError(err: unknown, apiUrl: string): string {
  const msg = err instanceof Error ? err.message : "Network error";
  if (msg.includes("Failed to fetch") || msg.includes("NetworkError") || msg.includes("aborted")) {
    if (apiUrl.includes("localhost")) {
      return (
        "Cannot reach API. Set NEXT_PUBLIC_API_URL on Vercel to " +
        PRODUCTION_API + " and redeploy."
      );
    }
    return (
      "API is still waking up on Render (free tier). Wait 30 seconds and click Start free trial again."
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

async function fetchApi(path: string, options: RequestInit, apiUrl: string): Promise<Response> {
  const url = `${apiUrl}${path}`;
  const maxAttempts = apiUrl.includes("localhost") ? 1 : 3;

  for (let attempt = 1; attempt <= maxAttempts; attempt++) {
    try {
      return await fetch(url, options);
    } catch (err) {
      if (attempt === maxAttempts) throw err;
      await wakeApi();
    }
  }

  throw new Error("Failed to fetch");
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
    res = await fetchApi(path, { ...options, headers }, apiUrl);
  } catch (err) {
    throw new Error(formatFetchError(err, apiUrl));
  }
  const data = await res.json().catch(() => ({}));

  if (!res.ok) {
    const detail = data.detail;
    const message =
      typeof detail === "string"
        ? detail === "Something went wrong. Please try again or contact support." && data.error
          ? String(data.error)
          : detail
        : Array.isArray(detail)
          ? detail.map((d: { msg?: string }) => d.msg).join(", ")
          : data.message || data.error || "Request failed";
    if (res.status === 401 && token && typeof window !== "undefined") {
      clearTokens();
      window.location.href = `/login?reason=${encodeURIComponent(message)}`;
    }
    throw new Error(message);
  }
  return data as T;
}

export const API_URL = getApiBaseUrl();

import { clearTokens, getAccessToken, getRefreshToken, setTokens } from "@/lib/auth-storage";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000";

type Envelope<T> = { status: number; message: string; data: T };

export class ApiError extends Error {
  status: number;
  data: unknown;

  constructor(message: string, status: number, data?: unknown) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.data = data;
  }
}

type RequestOptions = Omit<RequestInit, "body"> & {
  body?: unknown;
  /** Attach the Bearer access token. Defaults to true. */
  auth?: boolean;
  /** Internal — prevents infinite refresh loops. */
  isRetry?: boolean;
};

let refreshPromise: Promise<string | null> | null = null;

async function refreshAccessToken(): Promise<string | null> {
  const refresh = getRefreshToken();
  if (!refresh) return null;

  if (!refreshPromise) {
    refreshPromise = (async () => {
      try {
        const res = await fetch(`${API_BASE_URL}/auth/token/refresh/`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ refresh }),
        });
        const json: Envelope<{ access: string; refresh: string }> = await res.json();
        if (!res.ok) return null;
        setTokens(json.data.access, json.data.refresh);
        return json.data.access;
      } catch {
        return null;
      } finally {
        refreshPromise = null;
      }
    })();
  }

  return refreshPromise;
}

export async function apiFetch<T = void>(path: string, options: RequestOptions = {}): Promise<T> {
  const { body, auth = true, isRetry, headers, ...rest } = options;

  const finalHeaders: Record<string, string> = {
    Accept: "application/json",
    ...(headers as Record<string, string> | undefined),
  };

  let fetchBody: BodyInit | undefined;
  if (body instanceof FormData) {
    fetchBody = body;
  } else if (body !== undefined) {
    finalHeaders["Content-Type"] = "application/json";
    fetchBody = JSON.stringify(body);
  }

  if (auth) {
    const token = getAccessToken();
    if (token) finalHeaders.Authorization = `Bearer ${token}`;
  }

  const res = await fetch(`${API_BASE_URL}${path}`, {
    ...rest,
    headers: finalHeaders,
    body: fetchBody,
  });

  if (res.status === 204) return undefined as T;

  let json: Envelope<T> | null = null;
  try {
    json = await res.json();
  } catch {
    json = null;
  }

  if (res.status === 401 && auth && !isRetry) {
    const newToken = await refreshAccessToken();
    if (newToken) {
      return apiFetch<T>(path, { ...options, isRetry: true });
    }
    clearTokens();
    if (typeof window !== "undefined" && window.location.pathname !== "/login") {
      window.location.href = "/login";
    }
  }

  if (!res.ok || (json && json.status >= 400)) {
    const message = json?.message || res.statusText || "Something went wrong.";
    throw new ApiError(message, json?.status ?? res.status, json?.data);
  }

  return (json?.data as T) ?? (undefined as T);
}

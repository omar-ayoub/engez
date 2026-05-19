import { useAuthStore } from "@/lib/auth";

const BASE_URL = "";

export class ApiError extends Error {
  status: number;
  data: Record<string, unknown>;
  constructor(status: number, message: string, data: Record<string, unknown> = {}) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.data = data;
  }
  get isConflict() { return this.status === 409; }
  get isNotFound() { return this.status === 404; }
  get isUnauthorized() { return this.status === 401; }
  get isValidationError() { return this.status === 422; }
}

export class ApiConflictError extends ApiError {
  currentVersion: number;
  currentStatus: string;
  constructor(data: { current_version: number; current_status: string }) {
    super(409, "Conflict: resource was modified", data as unknown as Record<string, unknown>);
    this.name = "ApiConflictError";
    this.currentVersion = data.current_version ?? 0;
    this.currentStatus = data.current_status ?? "unknown";
  }
}

async function refreshAccessToken(): Promise<string | null> {
  try {
    const res = await fetch(`${BASE_URL}/api/v1/auth/refresh`, {
      method: "POST",
      credentials: "include",
    });
    if (!res.ok) return null;
    const data = await res.json();
    return data.access_token;
  } catch {
    return null;
  }
}

export async function request(
  url: string,
  options: RequestInit = {},
): Promise<Response> {
  const auth = useAuthStore.getState();

  const headers = new Headers(options.headers);
  if (auth.accessToken) {
    headers.set("Authorization", `Bearer ${auth.accessToken}`);
  }
  if (!headers.has("Content-Type") && options.body) {
    headers.set("Content-Type", "application/json");
  }

  let res = await fetch(`${BASE_URL}${url}`, {
    ...options,
    headers,
    credentials: "include",
  });

  if (res.status === 401) {
    const newToken = await refreshAccessToken();
    if (newToken) {
      auth.setAccessToken(newToken);
      headers.set("Authorization", `Bearer ${newToken}`);
      res = await fetch(`${BASE_URL}${url}`, {
        ...options,
        headers,
        credentials: "include",
      });
    } else {
      auth.logout();
      window.location.href = "/login";
    }
  }

  return res;
}

async function handleResponse<T>(res: Response): Promise<T> {
  if (res.status === 409) {
    const data = await res.json().catch(() => ({}));
    throw new ApiConflictError({
      current_version: data.current_version ?? 0,
      current_status: data.current_status ?? "unknown",
    });
  }
  if (!res.ok) {
    const data = await res.json().catch(() => ({}));
    const message = data.detail_en || data.detail || `API error: ${res.status}`;
    throw new ApiError(res.status, message, data);
  }
  return res.json();
}

export const api = {
  async get<T>(url: string): Promise<T> {
    const res = await request(url);
    return handleResponse<T>(res);
  },

  async post<T>(url: string, body?: unknown): Promise<T> {
    const res = await request(url, {
      method: "POST",
      body: body ? JSON.stringify(body) : undefined,
    });
    return handleResponse<T>(res);
  },

  async patch<T>(url: string, body?: unknown): Promise<T> {
    const res = await request(url, {
      method: "PATCH",
      body: body ? JSON.stringify(body) : undefined,
    });
    return handleResponse<T>(res);
  },

  async delete<T>(url: string): Promise<T> {
    const res = await request(url, { method: "DELETE" });
    return handleResponse<T>(res);
  },

  async put<T>(url: string, body?: unknown): Promise<T> {
    const res = await request(url, {
      method: "PUT",
      body: body ? JSON.stringify(body) : undefined,
    });
    return handleResponse<T>(res);
  },
};

const BASE_URL = "";

interface ApiError {
  detail?: string;
  detail_en?: string;
  [key: string]: unknown;
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

async function request(
  url: string,
  options: RequestInit = {}
): Promise<Response> {
  const { useAuthStore } = await import("@/lib/auth");
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

export const api = {
  async get<T>(url: string): Promise<T> {
    const res = await request(url);
    return res.json();
  },

  async post<T>(url: string, body?: unknown): Promise<T> {
    const res = await request(url, {
      method: "POST",
      body: body ? JSON.stringify(body) : undefined,
    });
    return res.json();
  },

  async patch<T>(url: string, body?: unknown): Promise<T> {
    const res = await request(url, {
      method: "PATCH",
      body: body ? JSON.stringify(body) : undefined,
    });
    return res.json();
  },

  async delete<T>(url: string): Promise<T> {
    const res = await request(url, { method: "DELETE" });
    return res.json();
  },
};

export type { ApiError };

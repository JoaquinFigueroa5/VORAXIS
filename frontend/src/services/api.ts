import { coded, has, t, type Coded } from "@/i18n";

const API_URL = import.meta.env.VITE_API_URL ?? "http://localhost:8000/api/v1";

/** `message` is written for people; `detail` keeps the backend's untranslated diagnostic. */
export class ApiError extends Error {
  constructor(
    readonly status: number,
    message: string,
    readonly code: string | null = null,
    readonly params: Record<string, unknown> | null = null,
    readonly detail: string | null = null,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

interface ErrorBody {
  error?: string;
  code?: string;
  params?: Record<string, unknown> | null;
  detail?: string;
}

function errorMessage(body: ErrorBody): string {
  const problems = body.params?.problems;
  if (body.code === "observations_incompatible" && Array.isArray(problems) && problems.length > 0) {
    return (problems as Coded[]).map((problem) => coded("api.incompatible", problem, t("api.error.observations_incompatible"))).join(" ");
  }
  if (body.code && has(`api.error.${body.code}`)) return coded("api.error", { code: body.code, params: body.params });
  return t("api.error.generic");
}

export async function apiFetch<T>(path: string, init: RequestInit = {}): Promise<T> {
  const response = await fetch(`${API_URL}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(init.headers ?? {}),
    },
  });

  if (!response.ok) {
    let body: ErrorBody | null = null;
    try {
      body = (await response.json()) as ErrorBody;
    } catch {
      // HTML or empty body (a proxy, or the server is down).
    }
    if (!body) throw new ApiError(response.status, t("api.error.generic"), null, null, response.statusText);
    throw new ApiError(response.status, errorMessage(body), body.code ?? null, body.params ?? null, body.detail ?? null);
  }

  if (response.status === 204) {
    return undefined as T;
  }
  return (await response.json()) as T;
}

export function buildQuery(params: Record<string, string | number | undefined | null>): string {
  const search = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined && value !== null && value !== "") {
      search.set(key, String(value));
    }
  }
  const query = search.toString();
  return query ? `?${query}` : "";
}

export { API_URL };

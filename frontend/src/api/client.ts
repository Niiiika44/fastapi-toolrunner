/**
 * Thin fetch wrapper around the AutoRunning API.
 *
 * Everything the app knows about transport lives here: where the API is, how
 * the bearer token is attached, and how the backend's error envelope
 * (`{"error": {"message": ...}}`, see app/core/error_handler.py) becomes an
 * exception the UI can render.
 */

/** Same origin in production, proxied by Vite in dev. */
export const API_BASE = "/api";

export class ApiError extends Error {
  readonly status: number;
  readonly payload: unknown;

  constructor(status: number, message: string, payload?: unknown) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.payload = payload;
  }

  /** The token is gone or expired — the app should drop it and re-login. */
  get isUnauthorized(): boolean {
    return this.status === 401;
  }

  get isForbidden(): boolean {
    return this.status === 403;
  }
}

type TokenReader = () => string | null;
type UnauthorizedHandler = () => void;

let readToken: TokenReader = () => null;
let onUnauthorized: UnauthorizedHandler = () => {};

/**
 * Wired once by the auth provider. Keeping it out of module state in React
 * would mean threading the token through every call site; keeping it here means
 * `api.get(...)` stays as short as `fetch`.
 */
export function configureApi(options: {
  getToken: TokenReader;
  onUnauthorized: UnauthorizedHandler;
}): void {
  readToken = options.getToken;
  onUnauthorized = options.onUnauthorized;
}

export function getToken(): string | null {
  return readToken();
}

function authHeader(): Record<string, string> {
  const token = readToken();
  return token ? { Authorization: `Bearer ${token}` } : {};
}

async function toApiError(response: Response): Promise<ApiError> {
  let payload: unknown = null;
  let message = `${response.status} ${response.statusText}`;

  try {
    payload = await response.json();
  } catch {
    return new ApiError(response.status, message);
  }

  // The backend normalises everything to {"error": {"message": ...}}, but a
  // 422 from FastAPI validation may still carry a `detail` array in `payload`.
  const body = payload as { error?: { message?: unknown }; detail?: unknown };
  if (body?.error && typeof body.error.message === "string") {
    message = body.error.message;
  } else if (typeof body?.detail === "string") {
    message = body.detail;
  } else if (Array.isArray(body?.detail)) {
    message = body.detail
      .map((item) => {
        const entry = item as { loc?: unknown[]; msg?: string };
        const field = Array.isArray(entry.loc) ? entry.loc.slice(1).join(".") : "";
        return field ? `${field}: ${entry.msg}` : (entry.msg ?? "invalid value");
      })
      .join("; ");
  }

  return new ApiError(response.status, message, payload);
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: { ...authHeader(), ...(init.headers ?? {}) },
  });

  if (response.status === 401) {
    onUnauthorized();
    throw await toApiError(response);
  }
  if (!response.ok) {
    throw await toApiError(response);
  }
  if (response.status === 204) {
    return undefined as T;
  }
  return (await response.json()) as T;
}

export const api = {
  get: <T>(path: string, init?: RequestInit) => request<T>(path, { ...init, method: "GET" }),

  post: <T>(path: string, body?: unknown) =>
    request<T>(path, {
      method: "POST",
      headers: body === undefined ? {} : { "Content-Type": "application/json" },
      body: body === undefined ? undefined : JSON.stringify(body),
    }),

  patch: <T>(path: string, body: unknown) =>
    request<T>(path, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    }),

  put: <T>(path: string, body: unknown) =>
    request<T>(path, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    }),

  delete: <T>(path: string) => request<T>(path, { method: "DELETE" }),

  /**
   * Multipart upload. The Content-Type header is deliberately not set: the
   * browser has to add it itself, because only it knows the boundary.
   */
  postMultipart: <T>(path: string, form: FormData) =>
    request<T>(path, { method: "POST", body: form }),

  /** `application/x-www-form-urlencoded` — what OAuth2PasswordRequestForm expects. */
  postForm: <T>(path: string, form: Record<string, string>) =>
    request<T>(path, {
      method: "POST",
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
      body: new URLSearchParams(form).toString(),
    }),
};

/** Serialises a filter object the way FastAPI reads list query parameters: repeated keys. */
export function toQueryString(params: Record<string, unknown>): string {
  const search = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value === undefined || value === null || value === "") continue;
    if (Array.isArray(value)) {
      for (const item of value) search.append(key, String(item));
    } else {
      search.append(key, String(value));
    }
  }
  const query = search.toString();
  return query ? `?${query}` : "";
}

const STORAGE_KEY = "autorunning.token";

export function readStoredToken(): string | null {
  try {
    return window.localStorage.getItem(STORAGE_KEY);
  } catch {
    // Private mode or blocked site data: the session simply does not survive a reload.
    return null;
  }
}

export function storeToken(token: string | null): void {
  try {
    if (token === null) window.localStorage.removeItem(STORAGE_KEY);
    else window.localStorage.setItem(STORAGE_KEY, token);
  } catch {
    /* ignore — the in-memory token still works for this tab */
  }
}

/**
 * Expiry of a JWT, in milliseconds, or null when the token carries no `exp`.
 * Reads the payload without verifying it: the signature is the server's
 * business, the UI only wants to know when to stop pretending it is logged in.
 */
export function tokenExpiresAt(token: string): number | null {
  const [, payload] = token.split(".");
  if (!payload) return null;
  try {
    const json = JSON.parse(
      atob(payload.replace(/-/g, "+").replace(/_/g, "/")),
    ) as { exp?: number };
    return typeof json.exp === "number" ? json.exp * 1000 : null;
  } catch {
    return null;
  }
}

export function isExpired(token: string): boolean {
  const expiresAt = tokenExpiresAt(token);
  return expiresAt !== null && expiresAt <= Date.now();
}

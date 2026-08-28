import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from "react";
import { useQueryClient } from "@tanstack/react-query";
import { configureApi } from "../api/client";
import { getMe, login as loginRequest, register as registerRequest } from "../api/auth";
import type { RegisterPayload } from "../api/auth";
import type { Permission, User } from "../api/types";
import { can as canWithUser } from "./permissions";
import { isExpired, readStoredToken, storeToken, tokenExpiresAt } from "./token";

interface AuthState {
  token: string | null;
  user: User | null;
  /** True until the stored token has been checked against /users/me. */
  loading: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (payload: RegisterPayload) => Promise<void>;
  logout: () => void;
  refreshUser: () => Promise<void>;
  can: (permission: Permission) => boolean;
}

const AuthContext = createContext<AuthState | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const stored = readStoredToken();
  const [token, setToken] = useState<string | null>(
    stored && !isExpired(stored) ? stored : null,
  );
  const [user, setUser] = useState<User | null>(null);
  const queryClient = useQueryClient();

  // Derived rather than stored on purpose. As a separate state it lagged one
  // render behind setToken, and in that render the guards saw a token with no
  // user — a signed-in session that looked signed out — and bounced back to
  // /login. "We have a token but not yet the user it belongs to" *is* loading,
  // and a failed /users/me clears the token, which ends the state by itself.
  const loading = token !== null && user === null;

  // The API layer reads the token through a ref so that configureApi is wired
  // once and never goes stale between renders.
  const tokenRef = useRef<string | null>(token);
  tokenRef.current = token;

  const logout = useCallback(() => {
    setToken(null);
    setUser(null);
    storeToken(null);
    queryClient.clear();
  }, [queryClient]);

  useEffect(() => {
    configureApi({
      getToken: () => tokenRef.current,
      // Any 401 means the token is no longer good — drop it rather than let the
      // app keep firing doomed requests.
      onUnauthorized: () => {
        if (tokenRef.current !== null) logout();
      },
    });
  }, [logout]);

  // There is no refresh token, so the session ends when the access token does.
  // Logging out on the exact second avoids a burst of 401s and a confusing UI.
  //
  // setTimeout truncates its delay to a 32-bit signed int: anything above
  // ~24.8 days overflows and fires immediately. ACCESS_TOKEN_EXPIRE_MINUTES is
  // free to be enormous, so the wait is split into chunks and re-armed until
  // the deadline is actually in range.
  useEffect(() => {
    if (!token) return;
    const expiresAt = tokenExpiresAt(token);
    if (expiresAt === null) return;

    const MAX_TIMEOUT = 2_147_483_647;
    let timer = 0;

    const arm = () => {
      const remaining = expiresAt - Date.now();
      if (remaining <= 0) {
        logout();
        return;
      }
      timer = window.setTimeout(arm, Math.min(remaining, MAX_TIMEOUT));
    };

    arm();
    return () => window.clearTimeout(timer);
  }, [token, logout]);

  const loadUser = useCallback(async () => {
    const me = await getMe();
    setUser(me);
  }, []);

  useEffect(() => {
    if (!token) {
      setUser(null);
      return;
    }
    let cancelled = false;
    loadUser().catch(() => {
      // The token is there but the server will not honour it: end the session
      // instead of leaving the app stuck on a spinner.
      if (!cancelled) logout();
    });
    return () => {
      cancelled = true;
    };
  }, [token, loadUser, logout]);

  const login = useCallback(async (email: string, password: string) => {
    const response = await loginRequest(email, password);
    tokenRef.current = response.access_token;
    storeToken(response.access_token);
    setToken(response.access_token);
  }, []);

  const register = useCallback(
    async (payload: RegisterPayload) => {
      await registerRequest(payload);
      await login(payload.email, payload.password);
    },
    [login],
  );

  const value = useMemo<AuthState>(
    () => ({
      token,
      user,
      loading,
      login,
      register,
      logout,
      refreshUser: loadUser,
      can: (permission: Permission) => canWithUser(user, permission),
    }),
    [token, user, loading, login, register, logout, loadUser],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthState {
  const context = useContext(AuthContext);
  if (!context) throw new Error("useAuth must be used inside <AuthProvider>");
  return context;
}

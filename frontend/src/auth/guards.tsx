import { Navigate, Outlet, useLocation } from "react-router-dom";
import type { Permission } from "../api/types";
import { useAuth } from "./AuthContext";
import { Spinner } from "../components/Spinner";

/** Blocks a route until there is a session; remembers where the user was headed. */
export function RequireAuth() {
  const { token, user, loading } = useAuth();
  const location = useLocation();

  if (loading) return <Spinner label="Restoring session" />;
  if (!token || !user) {
    return <Navigate to="/login" replace state={{ from: location.pathname }} />;
  }
  return <Outlet />;
}

/**
 * Route-level permission check, "any of" — the Users page, for instance, is
 * useful to a moderator (`user:update_any`) and to a reader (`user:read_any`)
 * alike, and each of them sees only the half they are allowed to use.
 *
 * The verdict is advisory (see permissions.ts): the server decides, this only
 * keeps users out of pages that would be empty.
 */
export function RequirePermission({ anyOf }: { anyOf: Permission[] }) {
  const { can } = useAuth();
  if (!anyOf.some(can)) return <Navigate to="/tests" replace />;
  return <Outlet />;
}

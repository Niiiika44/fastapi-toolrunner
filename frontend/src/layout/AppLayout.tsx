import { NavLink, Outlet } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";
import { fullName } from "../lib/format";
import { Button } from "../components/ui";
import { Avatar } from "../components/Avatar";

/**
 * Two rows on purpose: the brand and the account are about *this session*, the
 * tabs are about *where you are*. Sharing one line made the site name read as
 * the first nav item.
 *
 * The active tab's underline sits on the header's own bottom border (-mb-px),
 * so the two lines meet instead of stacking.
 */
function tabClass({ isActive }: { isActive: boolean }): string {
  return `whitespace-nowrap border-b-2 px-1 pb-2.5 pt-1 text-sm font-medium transition ${
    isActive
      ? "border-accent text-ink"
      : "border-transparent text-ink-muted hover:border-line hover:text-ink"
  }`;
}

export function AppLayout() {
  const { user, logout, can } = useAuth();

  return (
    <div className="flex min-h-full flex-col">
      <header className="border-b border-line bg-surface-raised">
        <div className="mx-auto max-w-7xl px-4">
          <div className="flex h-14 items-center justify-between gap-4">
            <NavLink to="/tests" className="flex items-center gap-2">
              <span className="size-2.5 rounded-sm bg-accent" aria-hidden />
              <span className="text-base font-semibold tracking-tight">AutoRunning</span>
            </NavLink>

            <div className="flex items-center gap-1">
              <NavLink
                to="/profile"
                className={({ isActive }) =>
                  `flex items-center gap-2 rounded-md px-2.5 py-1.5 text-sm transition ${
                    isActive ? "text-ink" : "text-ink-muted hover:text-ink"
                  }`
                }
              >
                {user && <Avatar user={user} size="md" />}
                <span className="hidden sm:inline">{user ? fullName(user) : "Profile"}</span>
              </NavLink>
              <Button variant="ghost" onClick={logout}>
                Sign out
              </Button>
            </div>
          </div>

          <nav className="-mb-px flex gap-6 overflow-x-auto">
            <NavLink to="/tests" className={tabClass}>
              Test cases
            </NavLink>
            {can("platform:read") && (
              <NavLink to="/platforms" className={tabClass}>
                Platforms
              </NavLink>
            )}
            {can("tag:manage") && (
              <NavLink to="/tags" className={tabClass}>
                Tags
              </NavLink>
            )}
            {(can("user:read_any") || can("user:update_any")) && (
              <NavLink to="/users" className={tabClass}>
                Users
              </NavLink>
            )}
          </nav>
        </div>
      </header>

      <main className="mx-auto w-full max-w-7xl flex-1 px-4 py-6">
        <Outlet />
      </main>
    </div>
  );
}

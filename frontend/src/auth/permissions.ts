import type { JobTitle, Permission, User } from "../api/types";

/**
 * What the signed-in account may do, straight from GET /users/me.
 *
 * This used to be a copy of ROLE_PERMISSIONS from the backend, because the API
 * exposed no effective permission set. A copy could only ever approximate the
 * server: it could not see individually granted permissions, so it hid controls
 * the user was in fact allowed to use, and it went stale whenever the role
 * table changed. Now there is nothing to keep in sync.
 */
export function permissionsOf(user: User | null): readonly Permission[] {
  return user?.permissions ?? [];
}

export function can(user: User | null, permission: Permission): boolean {
  return permissionsOf(user).includes(permission);
}

export const JOB_TITLES: JobTitle[] = ["developer", "tester", "analyst", "manager", "other"];

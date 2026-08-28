import { api } from "./client";
import type { JobTitle, Permission, User, UserPermissionGrant } from "./types";

export function listUsers(): Promise<User[]> {
  return api.get<User[]>("/users");
}

export function listRoleRequests(): Promise<User[]> {
  return api.get<User[]>("/users/role-requests");
}

export function getUser(userId: string): Promise<User> {
  return api.get<User>(`/users/${userId}`);
}

export function updateUser(
  userId: string,
  data: { first_name?: string; last_name?: string },
): Promise<User> {
  return api.patch<User>(`/users/${userId}`, data);
}

export function changePassword(
  userId: string,
  oldPassword: string,
  newPassword: string,
): Promise<User> {
  return api.post<User>(`/users/${userId}/change-password`, {
    old_password: oldPassword,
    new_password: newPassword,
  });
}

export function changeEmail(userId: string, newEmail: string, password: string): Promise<User> {
  return api.post<User>(`/users/${userId}/change-email`, {
    new_email: newEmail,
    password,
  });
}

export function deleteUser(userId: string): Promise<void> {
  return api.delete<void>(`/users/${userId}`);
}

export function requestRole(jobTitle: JobTitle): Promise<User> {
  return api.post<User>("/users/me/role-request", { job_title: jobTitle });
}

/**
 * `expected_job_title` guards against approving a request the moderator did not
 * actually see: the backend answers 409 if the user changed it meanwhile.
 */
export function approveRoleRequest(userId: string, expected: JobTitle): Promise<User> {
  return api.post<User>(`/users/${userId}/role-request/approve`, {
    expected_job_title: expected,
  });
}

export function rejectRoleRequest(userId: string): Promise<User> {
  return api.post<User>(`/users/${userId}/role-request/reject`);
}

/** Takes back your own pending request. Idempotent. */
export function withdrawRoleRequest(): Promise<void> {
  return api.delete<void>("/users/me/role-request");
}

export function assignRole(userId: string, jobTitle: JobTitle): Promise<User> {
  return api.put<User>(`/users/${userId}/role`, { job_title: jobTitle });
}

/** Superuser only. */
export function listUserPermissions(userId: string): Promise<UserPermissionGrant[]> {
  return api.get<UserPermissionGrant[]>(`/users/${userId}/permissions`);
}

export function grantPermission(userId: string, permission: Permission): Promise<void> {
  return api.post<void>(`/users/${userId}/permissions/${encodeURIComponent(permission)}`);
}

export function revokePermission(userId: string, permission: Permission): Promise<void> {
  return api.delete<void>(`/users/${userId}/permissions/${encodeURIComponent(permission)}`);
}

/**
 * Replaces the avatar of an account. Allowed for the owner and for holders of
 * `user:update_any`. Returns the updated user, so `avatar_url` comes back
 * already pointing at the new picture.
 */
export function uploadAvatar(userId: string, file: File): Promise<User> {
  const form = new FormData();
  form.append("file", file);
  return api.postMultipart<User>(`/users/${userId}/avatar`, form);
}

export function deleteAvatar(userId: string): Promise<void> {
  return api.delete<void>(`/users/${userId}/avatar`);
}

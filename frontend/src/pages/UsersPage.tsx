import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  approveRoleRequest,
  assignRole,
  deleteUser,
  grantPermission,
  listRoleRequests,
  listUserPermissions,
  listUsers,
  rejectRoleRequest,
  revokePermission,
} from "../api/users";
import { PERMISSIONS } from "../api/types";
import type { JobTitle, Permission, User } from "../api/types";
import { useAuth } from "../auth/AuthContext";
import { JOB_TITLES } from "../auth/permissions";
import { fullName } from "../lib/format";
import { Badge, Button, Card, CardHeader, EmptyState, ErrorBanner, Select } from "../components/ui";
import { Spinner } from "../components/Spinner";
import { Avatar } from "../components/Avatar";
import { Modal } from "../components/Modal";
import { useToast } from "../components/Toast";

export function UsersPage() {
  const { user: me, can } = useAuth();
  const queryClient = useQueryClient();
  const toast = useToast();
  const [error, setError] = useState<unknown>(null);
  const [permissionsFor, setPermissionsFor] = useState<User | null>(null);

  const mayModerate = can("user:update_any");
  const mayList = can("user:read_any");

  const users = useQuery({ queryKey: ["users"], queryFn: listUsers, enabled: mayList });
  const requests = useQuery({
    queryKey: ["role-requests"],
    queryFn: listRoleRequests,
    enabled: mayModerate,
  });

  function invalidateUsers() {
    void queryClient.invalidateQueries({ queryKey: ["users"] });
    void queryClient.invalidateQueries({ queryKey: ["role-requests"] });
  }

  const approve = useMutation({
    mutationFn: ({ id, expected }: { id: string; expected: JobTitle }) =>
      approveRoleRequest(id, expected),
    onSuccess: () => {
      setError(null);
      toast("Role approved.", "success");
      invalidateUsers();
    },
    // 409 means the request changed under the moderator's feet — refresh so the
    // list stops showing a decision that no longer applies.
    onError: (cause) => {
      setError(cause);
      invalidateUsers();
    },
  });

  const reject = useMutation({
    mutationFn: (id: string) => rejectRoleRequest(id),
    onSuccess: () => {
      setError(null);
      toast("Role request rejected.", "success");
      invalidateUsers();
    },
    onError: setError,
  });

  const setRole = useMutation({
    mutationFn: ({ id, role }: { id: string; role: JobTitle }) => assignRole(id, role),
    onSuccess: () => {
      setError(null);
      toast("Role assigned.", "success");
      invalidateUsers();
    },
    onError: setError,
  });

  const remove = useMutation({
    mutationFn: (id: string) => deleteUser(id),
    onSuccess: () => {
      setError(null);
      toast("User deleted.", "success");
      invalidateUsers();
    },
    onError: setError,
  });

  return (
    <div className="space-y-4">
      <h1 className="text-lg font-semibold tracking-tight">Users</h1>

      <ErrorBanner error={error} />

      {mayModerate && (
        <Card>
          <CardHeader
            title="Pending role requests"
            action={<span className="text-xs text-ink-muted">{requests.data?.length ?? 0}</span>}
          />
          {requests.isPending ? (
            <Spinner label="Loading requests" />
          ) : requests.data && requests.data.length === 0 ? (
            <EmptyState title="No pending requests" />
          ) : (
            <ul className="divide-y divide-line/60">
              {requests.data?.map((user) => (
                <li
                  key={user.id}
                  className="flex flex-wrap items-center gap-3 px-4 py-3 text-sm"
                >
                  <div className="flex items-center gap-3">
                    <Avatar user={user} size="md" />
                    <div>
                      <p className="font-medium">{fullName(user)}</p>
                      <p className="text-xs text-ink-muted">{user.email}</p>
                    </div>
                  </div>
                  <p className="text-ink-muted">
                    <Badge>{user.job_title}</Badge> → <Badge tone="warn">{user.requested_job_title}</Badge>
                  </p>
                  <div className="ml-auto flex gap-2">
                    <Button
                      variant="primary"
                      loading={approve.isPending && approve.variables?.id === user.id}
                      onClick={() =>
                        user.requested_job_title &&
                        approve.mutate({ id: user.id, expected: user.requested_job_title })
                      }
                    >
                      Approve
                    </Button>
                    <Button
                      loading={reject.isPending && reject.variables === user.id}
                      onClick={() => reject.mutate(user.id)}
                    >
                      Reject
                    </Button>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </Card>
      )}

      {mayList && (
        <Card>
          <CardHeader title="All users" />
          {users.isPending ? (
            <Spinner label="Loading users" />
          ) : users.data && users.data.length === 0 ? (
            <EmptyState title="No users" />
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full min-w-[44rem] text-sm">
                <thead className="border-b border-line text-left text-xs uppercase tracking-wide text-ink-muted">
                  <tr>
                    <th className="px-4 py-2 font-medium">User</th>
                    <th className="px-4 py-2 font-medium">Role</th>
                    <th className="px-4 py-2 font-medium">Requested</th>
                    <th className="px-4 py-2 font-medium"></th>
                  </tr>
                </thead>
                <tbody>
                  {users.data?.map((user) => (
                    <tr key={user.id} className="border-b border-line/60 last:border-0">
                      <td className="px-4 py-2">
                        <div className="flex items-center gap-3">
                          <Avatar user={user} size="md" />
                          <div>
                            <p className="font-medium">
                              {fullName(user)}
                              {user.id === me?.id && (
                                <span className="ml-2 text-xs text-ink-muted">(you)</span>
                              )}
                            </p>
                            <p className="text-xs text-ink-muted">{user.email}</p>
                          </div>
                        </div>
                      </td>
                      <td className="px-4 py-2">
                        {mayModerate ? (
                          <Select
                            value={user.job_title}
                            onChange={(event) =>
                              setRole.mutate({
                                id: user.id,
                                role: event.target.value as JobTitle,
                              })
                            }
                            className="w-36"
                          >
                            {JOB_TITLES.map((title) => (
                              <option key={title} value={title}>
                                {title}
                              </option>
                            ))}
                          </Select>
                        ) : (
                          <Badge>{user.job_title}</Badge>
                        )}
                        {user.is_superuser && (
                          <span className="ml-2">
                            <Badge tone="good">superuser</Badge>
                          </span>
                        )}
                      </td>
                      <td className="px-4 py-2">
                        {user.requested_job_title ? (
                          <Badge tone="warn">{user.requested_job_title}</Badge>
                        ) : (
                          <span className="text-ink-muted">—</span>
                        )}
                      </td>
                      <td className="px-4 py-2">
                        <div className="flex justify-end gap-2">
                          {me?.is_superuser && (
                            <Button onClick={() => setPermissionsFor(user)}>Permissions</Button>
                          )}
                          {can("user:delete_any") && user.id !== me?.id && (
                            <Button
                              variant="danger"
                              loading={remove.isPending && remove.variables === user.id}
                              onClick={() => {
                                if (
                                  window.confirm(
                                    `Delete ${fullName(user)}? Their uploaded test cases stay.`,
                                  )
                                ) {
                                  remove.mutate(user.id);
                                }
                              }}
                            >
                              Delete
                            </Button>
                          )}
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </Card>
      )}

      <PermissionsDialog user={permissionsFor} onClose={() => setPermissionsFor(null)} />
    </div>
  );
}

/** Individual grants sit on top of the role baseline; superuser only. */
function PermissionsDialog({ user, onClose }: { user: User | null; onClose: () => void }) {
  const queryClient = useQueryClient();
  const toast = useToast();
  const [error, setError] = useState<unknown>(null);

  const grants = useQuery({
    queryKey: ["user-permissions", user?.id],
    queryFn: () => listUserPermissions(user!.id),
    enabled: user !== null,
  });

  const granted = new Set(grants.data?.map((grant) => grant.permission));

  function invalidate() {
    void queryClient.invalidateQueries({ queryKey: ["user-permissions", user?.id] });
  }

  const grant = useMutation({
    mutationFn: (permission: Permission) => grantPermission(user!.id, permission),
    onSuccess: () => {
      setError(null);
      toast("Permission granted.", "success");
      invalidate();
    },
    onError: setError,
  });

  const revoke = useMutation({
    mutationFn: (permission: Permission) => revokePermission(user!.id, permission),
    onSuccess: () => {
      setError(null);
      toast("Permission revoked.", "success");
      invalidate();
    },
    onError: setError,
  });

  return (
    <Modal
      open={user !== null}
      title={user ? `Permissions of ${fullName(user)}` : "Permissions"}
      onClose={onClose}
    >
      {grants.isPending && user ? (
        <Spinner label="Loading grants" />
      ) : (
        <div className="space-y-3">
          <p className="text-xs text-ink-muted">
            These are grants on top of the <strong>{user?.job_title}</strong> role baseline. The
            baseline itself is not listed by the API.
          </p>
          <ErrorBanner error={error} />
          <ul className="divide-y divide-line/60">
            {PERMISSIONS.map((permission) => {
              const isGranted = granted.has(permission);
              return (
                <li key={permission} className="flex items-center justify-between py-2 text-sm">
                  <span className={isGranted ? "font-medium" : "text-ink-muted"}>{permission}</span>
                  {isGranted ? (
                    <Button
                      variant="danger"
                      loading={revoke.isPending && revoke.variables === permission}
                      onClick={() => revoke.mutate(permission)}
                    >
                      Revoke
                    </Button>
                  ) : (
                    <Button
                      loading={grant.isPending && grant.variables === permission}
                      onClick={() => grant.mutate(permission)}
                    >
                      Grant
                    </Button>
                  )}
                </li>
              );
            })}
          </ul>
        </div>
      )}
    </Modal>
  );
}

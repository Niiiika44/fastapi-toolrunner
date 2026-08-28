import { useRef, useState, type FormEvent } from "react";
import { useMutation } from "@tanstack/react-query";
import {
  changeEmail,
  changePassword,
  deleteAvatar,
  requestRole,
  updateUser,
  uploadAvatar,
  withdrawRoleRequest,
} from "../api/users";
import type { JobTitle, User } from "../api/types";
import { useAuth } from "../auth/AuthContext";
import { JOB_TITLES, permissionsOf } from "../auth/permissions";
import { Badge, Button, Card, CardHeader, ErrorBanner, Field, Input, Select } from "../components/ui";
import { useToast } from "../components/Toast";
import { formatBytes } from "../lib/format";
import { Avatar } from "../components/Avatar";

export function ProfilePage() {
  const { user } = useAuth();
  // The forms are keyed by the account they edit, so the inner component can
  // seed its state from the user without juggling optional values.
  if (!user) return null;
  return <ProfileForms key={user.id} user={user} />;
}

function ProfileForms({ user }: { user: User }) {
  const { refreshUser, logout } = useAuth();
  const toast = useToast();
  const [error, setError] = useState<unknown>(null);

  const [firstName, setFirstName] = useState(user.first_name);
  const [lastName, setLastName] = useState(user.last_name);
  const [oldPassword, setOldPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [emailPassword, setEmailPassword] = useState("");
  const [newEmail, setNewEmail] = useState("");
  const [role, setRole] = useState<JobTitle>(user.job_title);

  const profile = useMutation({
    mutationFn: () => updateUser(user.id, { first_name: firstName, last_name: lastName }),
    onSuccess: async () => {
      setError(null);
      toast("Profile updated.", "success");
      await refreshUser();
    },
    onError: setError,
  });

  const password = useMutation({
    mutationFn: () => changePassword(user.id, oldPassword, newPassword),
    onSuccess: () => {
      setError(null);
      setOldPassword("");
      setNewPassword("");
      toast("Password changed.", "success");
    },
    onError: setError,
  });

  const email = useMutation({
    mutationFn: () => changeEmail(user.id, newEmail, emailPassword),
    onSuccess: () => {
      setError(null);
      setEmailPassword("");
      // The username is re-derived from the new address, so the safest thing is
      // to start a fresh session rather than keep a token issued for the old one.
      toast("Email changed — please sign in again.", "success");
      logout();
    },
    onError: setError,
  });

  const withdraw = useMutation({
    mutationFn: withdrawRoleRequest,
    onSuccess: async () => {
      setError(null);
      toast("Role request withdrawn.", "success");
      await refreshUser();
    },
    onError: setError,
  });

  const roleRequest = useMutation({
    mutationFn: () => requestRole(role),
    onSuccess: async () => {
      setError(null);
      toast("Role request sent. A moderator has to approve it.", "success");
      await refreshUser();
    },
    onError: setError,
  });

  const submit = (action: { mutate: () => void }) => (event: FormEvent) => {
    event.preventDefault();
    action.mutate();
  };

  return (
    <div className="mx-auto max-w-2xl space-y-4">
      <h1 className="text-lg font-semibold tracking-tight">Profile</h1>

      <ErrorBanner error={error} />

      <AvatarCard user={user} onError={setError} />

      <Card>
        <CardHeader title="Access" />
        <div className="space-y-3 p-4 text-sm">
          <p className="text-ink-muted">
            {user.email} · role <Badge tone="info">{user.job_title}</Badge>
            {user.is_superuser && (
              <>
                {" "}
                <Badge tone="good">superuser</Badge>
              </>
            )}
          </p>
          {user.requested_job_title && (
            <p className="flex flex-wrap items-center gap-2 text-ink-muted">
              Pending request: <Badge tone="warn">{user.requested_job_title}</Badge>
              <Button
                variant="ghost"
                loading={withdraw.isPending}
                onClick={() => withdraw.mutate()}
              >
                Withdraw
              </Button>
            </p>
          )}
          <div className="flex flex-wrap gap-1.5">
            {permissionsOf(user).map((permission) => (
              <Badge key={permission}>{permission}</Badge>
            ))}
          </div>
          <p className="text-xs text-ink-muted">
            Exactly what the server will allow, role baseline and individual grants together.
          </p>
        </div>
      </Card>

      <Card>
        <CardHeader title="Name" />
        <form onSubmit={submit(profile)} className="space-y-3 p-4">
          <div className="grid gap-3 sm:grid-cols-2">
            <Field label="First name">
              <Input
                value={firstName}
                minLength={2}
                maxLength={50}
                onChange={(event) => setFirstName(event.target.value)}
              />
            </Field>
            <Field label="Last name">
              <Input
                value={lastName}
                minLength={2}
                maxLength={50}
                onChange={(event) => setLastName(event.target.value)}
              />
            </Field>
          </div>
          <Button type="submit" variant="primary" loading={profile.isPending}>
            Save
          </Button>
        </form>
      </Card>

      <Card>
        <CardHeader title="Password" />
        <form onSubmit={submit(password)} className="space-y-3 p-4">
          <Field label="Current password">
            <Input
              type="password"
              autoComplete="current-password"
              required
              minLength={8}
              value={oldPassword}
              onChange={(event) => setOldPassword(event.target.value)}
            />
          </Field>
          <Field label="New password" hint="8 to 50 characters.">
            <Input
              type="password"
              autoComplete="new-password"
              required
              minLength={8}
              maxLength={50}
              value={newPassword}
              onChange={(event) => setNewPassword(event.target.value)}
            />
          </Field>
          <Button type="submit" variant="primary" loading={password.isPending}>
            Change password
          </Button>
        </form>
      </Card>

      <Card>
        <CardHeader title="Email" />
        <form onSubmit={submit(email)} className="space-y-3 p-4">
          <Field label="New email" hint="Only @ispras.ru addresses are accepted.">
            <Input
              type="email"
              required
              value={newEmail}
              onChange={(event) => setNewEmail(event.target.value)}
            />
          </Field>
          <Field label="Current password">
            <Input
              type="password"
              autoComplete="current-password"
              required
              minLength={8}
              value={emailPassword}
              onChange={(event) => setEmailPassword(event.target.value)}
            />
          </Field>
          <Button type="submit" variant="primary" loading={email.isPending}>
            Change email
          </Button>
        </form>
      </Card>

      <Card>
        <CardHeader title="Role" />
        <form onSubmit={submit(roleRequest)} className="space-y-3 p-4">
          <Field
            label="Request a different role"
            hint="Takes effect only after a moderator approves it."
          >
            <Select value={role} onChange={(event) => setRole(event.target.value as JobTitle)}>
              {JOB_TITLES.map((title) => (
                <option key={title} value={title}>
                  {title}
                </option>
              ))}
            </Select>
          </Field>
          <Button
            type="submit"
            variant="primary"
            loading={roleRequest.isPending}
            disabled={role === user.job_title}
          >
            Send request
          </Button>
        </form>
      </Card>
    </div>
  );
}

/**
 * Accepted image types and size cap, mirrored by the backend.
 *
 * 10 MB matches the global client_max_body_size in nginx, so the app and the
 * proxy reject the same files. It is generous for a picture that renders at
 * 80 px because the server re-encodes: what ends up stored is bounded by the
 * resize, not by this number.
 */
const AVATAR_TYPES = ["image/png", "image/jpeg", "image/webp"];
const AVATAR_MAX_BYTES = 10 * 1024 * 1024;

function AvatarCard({ user, onError }: { user: User; onError: (error: unknown) => void }) {
  const { refreshUser } = useAuth();
  const toast = useToast();
  const inputRef = useRef<HTMLInputElement>(null);

  const upload = useMutation({
    mutationFn: (file: File) => uploadAvatar(user.id, file),
    onSuccess: async () => {
      onError(null);
      toast("Photo updated.", "success");
      await refreshUser();
    },
    onError,
  });

  const remove = useMutation({
    mutationFn: () => deleteAvatar(user.id),
    onSuccess: async () => {
      onError(null);
      toast("Photo removed.", "success");
      await refreshUser();
    },
    onError,
  });

  // Checked here as well as on the server: rejecting a 5 MB file after it has
  // been uploaded is a waste of the user's time, not a security measure.
  function pick(file: File | undefined) {
    if (!file) return;
    if (!AVATAR_TYPES.includes(file.type)) {
      onError(new Error("Only PNG, JPEG and WebP images are accepted."));
      return;
    }
    if (file.size > AVATAR_MAX_BYTES) {
      onError(
        new Error(
          `${formatBytes(file.size)} exceeds the ${formatBytes(AVATAR_MAX_BYTES)} limit.`,
        ),
      );
      return;
    }
    upload.mutate(file);
  }

  return (
    <Card>
      <CardHeader title="Photo" />
      <div className="flex flex-wrap items-center gap-5 p-4">
        <Avatar user={user} size="lg" />
        <div className="space-y-2">
          <div className="flex gap-2">
            <input
              ref={inputRef}
              type="file"
              accept={AVATAR_TYPES.join(",")}
              hidden
              onChange={(event) => {
                pick(event.target.files?.[0]);
                // Let the same file be picked again after a failed attempt.
                event.target.value = "";
              }}
            />
            <Button
              variant="primary"
              loading={upload.isPending}
              onClick={() => inputRef.current?.click()}
            >
              {user.avatar_url ? "Replace" : "Upload"}
            </Button>
            {user.avatar_url && (
              <Button variant="danger" loading={remove.isPending} onClick={() => remove.mutate()}>
                Remove
              </Button>
            )}
          </div>
          <p className="text-xs text-ink-muted">
            PNG, JPEG or WebP, up to {formatBytes(AVATAR_MAX_BYTES)}. Without a photo you get
            initials on a colour derived from your account id.
          </p>
        </div>
      </div>
    </Card>
  );
}

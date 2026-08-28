import { useState, type FormEvent } from "react";
import { Link, Navigate, useNavigate } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";
import { JOB_TITLES } from "../auth/permissions";
import type { JobTitle } from "../api/types";
import { Button, Card, ErrorBanner, Field, Input, Select } from "../components/ui";
import { useToast } from "../components/Toast";

export function RegisterPage() {
  const { token, register } = useAuth();
  const navigate = useNavigate();
  const toast = useToast();
  const [form, setForm] = useState({
    email: "",
    password: "",
    first_name: "",
    last_name: "",
    job_title: "developer" as JobTitle,
  });
  const [error, setError] = useState<unknown>(null);
  const [busy, setBusy] = useState(false);

  if (token) return <Navigate to="/tests" replace />;

  function update<K extends keyof typeof form>(key: K, value: (typeof form)[K]) {
    setForm((current) => ({ ...current, [key]: value }));
  }

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    setBusy(true);
    try {
      await register(form);
      toast(
        "Account created with read-only access. The role you picked is a request a moderator has to approve.",
        "success",
      );
      navigate("/tests", { replace: true });
    } catch (cause) {
      setError(cause);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="mx-auto flex min-h-full max-w-md flex-col justify-center px-4 py-12">
      <h1 className="mb-6 text-xl font-semibold tracking-tight">Create an account</h1>
      <Card className="p-5">
        <form onSubmit={onSubmit} className="space-y-4">
          <div className="grid grid-cols-2 gap-3">
            <Field label="First name">
              <Input
                required
                minLength={2}
                maxLength={50}
                value={form.first_name}
                onChange={(event) => update("first_name", event.target.value)}
              />
            </Field>
            <Field label="Last name">
              <Input
                required
                minLength={2}
                maxLength={50}
                value={form.last_name}
                onChange={(event) => update("last_name", event.target.value)}
              />
            </Field>
          </div>
          <Field label="Email" hint="Only @ispras.ru addresses are accepted.">
            <Input
              type="email"
              autoComplete="username"
              required
              value={form.email}
              onChange={(event) => update("email", event.target.value)}
              placeholder="you@ispras.ru"
            />
          </Field>
          <Field label="Password" hint="8 to 50 characters.">
            <Input
              type="password"
              autoComplete="new-password"
              required
              minLength={8}
              maxLength={50}
              value={form.password}
              onChange={(event) => update("password", event.target.value)}
            />
          </Field>
          <Field
            label="Role"
            hint="New accounts start read-only; this is a request for a moderator to approve."
          >
            <Select
              value={form.job_title}
              onChange={(event) => update("job_title", event.target.value as JobTitle)}
            >
              {JOB_TITLES.map((title) => (
                <option key={title} value={title}>
                  {title}
                </option>
              ))}
            </Select>
          </Field>
          <ErrorBanner error={error} />
          <Button type="submit" variant="primary" loading={busy} className="w-full">
            Register
          </Button>
        </form>
      </Card>
      <p className="mt-4 text-center text-sm text-ink-muted">
        Already registered?{" "}
        <Link to="/login" className="text-accent hover:underline">
          Sign in
        </Link>
      </p>
    </div>
  );
}

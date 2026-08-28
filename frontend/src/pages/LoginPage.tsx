import { useState, type FormEvent } from "react";
import { Link, Navigate, useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";
import { Button, Card, ErrorBanner, Field, Input } from "../components/ui";

export function LoginPage() {
  const { token, login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<unknown>(null);
  const [busy, setBusy] = useState(false);

  if (token) return <Navigate to="/tests" replace />;

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    setBusy(true);
    try {
      await login(email, password);
      const from = (location.state as { from?: string } | null)?.from;
      navigate(from ?? "/tests", { replace: true });
    } catch (cause) {
      setError(cause);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="mx-auto flex min-h-full max-w-md flex-col justify-center px-4 py-12">
      <h1 className="mb-6 text-xl font-semibold tracking-tight">AutoRunning</h1>
      <Card className="p-5">
        <form onSubmit={onSubmit} className="space-y-4">
          <Field label="Email">
            <Input
              type="email"
              autoComplete="username"
              required
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              placeholder="you@ispras.ru"
            />
          </Field>
          <Field label="Password">
            <Input
              type="password"
              autoComplete="current-password"
              required
              value={password}
              onChange={(event) => setPassword(event.target.value)}
            />
          </Field>
          <ErrorBanner error={error} />
          <Button type="submit" variant="primary" loading={busy} className="w-full">
            Sign in
          </Button>
        </form>
      </Card>
      <p className="mt-4 text-center text-sm text-ink-muted">
        No account?{" "}
        <Link to="/register" className="text-accent hover:underline">
          Register
        </Link>
      </p>
    </div>
  );
}

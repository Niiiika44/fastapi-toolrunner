import type { ButtonHTMLAttributes, InputHTMLAttributes, ReactNode, SelectHTMLAttributes } from "react";
import { InlineSpinner } from "./Spinner";

type Variant = "primary" | "secondary" | "ghost" | "danger";

const VARIANTS: Record<Variant, string> = {
  primary: "bg-accent text-accent-ink hover:opacity-90 disabled:opacity-50",
  secondary:
    "border border-line bg-surface-raised text-ink hover:border-ink-muted disabled:opacity-50",
  ghost: "text-ink-muted hover:text-ink hover:bg-line/40 disabled:opacity-50",
  danger:
    "border border-red-500/40 text-red-600 hover:bg-red-500/10 disabled:opacity-50 dark:text-red-400",
};

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant;
  loading?: boolean;
}

export function Button({
  variant = "secondary",
  loading = false,
  disabled,
  children,
  className = "",
  ...rest
}: ButtonProps) {
  return (
    <button
      {...rest}
      disabled={disabled || loading}
      className={`inline-flex items-center justify-center gap-2 rounded-md px-3 py-1.5 text-sm font-medium transition disabled:cursor-not-allowed ${VARIANTS[variant]} ${className}`}
    >
      {loading && <InlineSpinner />}
      {children}
    </button>
  );
}

export function Field({
  label,
  hint,
  error,
  children,
}: {
  label: string;
  hint?: string;
  error?: string;
  children: ReactNode;
}) {
  return (
    <label className="block space-y-1.5">
      <span className="block text-sm font-medium text-ink">{label}</span>
      {children}
      {error ? (
        <span className="block text-xs text-red-600 dark:text-red-400">{error}</span>
      ) : hint ? (
        <span className="block text-xs text-ink-muted">{hint}</span>
      ) : null}
    </label>
  );
}

const CONTROL =
  "w-full rounded-md border border-line bg-surface-raised px-3 py-1.5 text-sm text-ink placeholder:text-ink-muted/70 disabled:opacity-60";

export function Input({ className = "", ...rest }: InputHTMLAttributes<HTMLInputElement>) {
  return <input {...rest} className={`${CONTROL} ${className}`} />;
}

export function Select({ className = "", children, ...rest }: SelectHTMLAttributes<HTMLSelectElement>) {
  return (
    <select {...rest} className={`${CONTROL} ${className}`}>
      {children}
    </select>
  );
}

export function Card({ children, className = "" }: { children: ReactNode; className?: string }) {
  return (
    <section
      className={`rounded-lg border border-line bg-surface-raised ${className}`}
    >
      {children}
    </section>
  );
}

export function CardHeader({ title, action }: { title: ReactNode; action?: ReactNode }) {
  return (
    <header className="flex items-center justify-between gap-3 border-b border-line px-4 py-3">
      <h2 className="text-sm font-semibold text-ink">{title}</h2>
      {action}
    </header>
  );
}

export function Badge({
  children,
  tone = "neutral",
}: {
  children: ReactNode;
  tone?: "neutral" | "good" | "bad" | "warn" | "info";
}) {
  const tones = {
    neutral: "bg-line/60 text-ink-muted",
    good: "bg-emerald-500/15 text-emerald-700 dark:text-emerald-400",
    bad: "bg-red-500/15 text-red-700 dark:text-red-400",
    warn: "bg-amber-500/15 text-amber-700 dark:text-amber-400",
    info: "bg-sky-500/15 text-sky-700 dark:text-sky-400",
  } as const;
  return (
    <span
      className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ${tones[tone]}`}
    >
      {children}
    </span>
  );
}

export function ErrorBanner({ error }: { error: unknown }) {
  if (!error) return null;
  const message = error instanceof Error ? error.message : String(error);
  return (
    <div
      role="alert"
      className="rounded-md border border-red-500/40 bg-red-500/10 px-3 py-2 text-sm text-red-700 dark:text-red-300"
    >
      {message}
    </div>
  );
}

export function EmptyState({ title, hint }: { title: string; hint?: string }) {
  return (
    <div className="px-4 py-12 text-center">
      <p className="text-sm font-medium text-ink">{title}</p>
      {hint && <p className="mt-1 text-sm text-ink-muted">{hint}</p>}
    </div>
  );
}

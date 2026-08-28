export function Spinner({ label }: { label?: string }) {
  return (
    <div className="flex items-center justify-center gap-3 p-8 text-ink-muted">
      <span
        className="inline-block size-4 animate-spin rounded-full border-2 border-line border-t-accent"
        aria-hidden
      />
      <span className="text-sm">{label ?? "Loading"}…</span>
    </div>
  );
}

export function InlineSpinner() {
  return (
    <span
      className="inline-block size-3.5 animate-spin rounded-full border-2 border-current/30 border-t-current"
      aria-hidden
    />
  );
}

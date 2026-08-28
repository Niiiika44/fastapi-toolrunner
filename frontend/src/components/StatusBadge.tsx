import type { TestStatus, ValidationStatus } from "../api/types";
import { Badge } from "./ui";

const TEST_TONE: Record<TestStatus, "neutral" | "info" | "good" | "bad"> = {
  pending: "neutral",
  processing: "info",
  parsed: "good",
  error: "bad",
};

export function TestStatusBadge({ status }: { status: TestStatus }) {
  return <Badge tone={TEST_TONE[status]}>{status}</Badge>;
}

const VALIDATION_TONE: Record<ValidationStatus, "neutral" | "info" | "good" | "bad"> = {
  pending: "neutral",
  running: "info",
  completed: "good",
  failed: "bad",
};

export function ValidationStatusBadge({ status }: { status: ValidationStatus }) {
  return <Badge tone={VALIDATION_TONE[status]}>{status}</Badge>;
}

/** The verdict of a finished run, which is separate from whether the run itself worked. */
export function VerdictBadge({ valid }: { valid: boolean | null }) {
  if (valid === null) return <Badge tone="neutral">no verdict</Badge>;
  return valid ? <Badge tone="good">valid</Badge> : <Badge tone="bad">invalid</Badge>;
}

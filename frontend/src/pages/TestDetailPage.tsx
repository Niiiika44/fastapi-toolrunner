import { useState, type ReactNode } from "react";
import { Link, useParams } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  attachTag,
  detachTag,
  downloadArtifact,
  downloadExport,
  getTest,
  listArtifacts,
  listValidations,
  requestValidation,
} from "../api/tests";
import { createTag, listTags } from "../api/tags";
import { ApiError } from "../api/client";
import type { Artifact, Tag, TestCase } from "../api/types";
import { useAuth } from "../auth/AuthContext";
import { useTestStatus } from "../lib/useTestStatus";
import { formatDateTime } from "../lib/format";
import { UserChip } from "../components/Avatar";
import {
  Badge,
  Button,
  Card,
  CardHeader,
  EmptyState,
  ErrorBanner,
  Input,
} from "../components/ui";
import { Spinner } from "../components/Spinner";
import { TestStatusBadge, ValidationStatusBadge, VerdictBadge } from "../components/StatusBadge";
import { useToast } from "../components/Toast";

export function TestDetailPage() {
  const { testId: rawId } = useParams();
  const testId = Number(rawId);
  const { can } = useAuth();
  const toast = useToast();
  const queryClient = useQueryClient();
  const [actionError, setActionError] = useState<unknown>(null);

  const test = useQuery({
    queryKey: ["test", testId],
    queryFn: () => getTest(testId),
    enabled: Number.isFinite(testId),
  });

  const validations = useQuery({
    queryKey: ["validations", testId],
    queryFn: () => listValidations(testId),
    enabled: Number.isFinite(testId),
  });

  // Live status only matters while the test case can still move; a parsed test
  // case with no running validation has nothing to push.
  const hasOpenWork =
    test.data?.status === "pending" ||
    test.data?.status === "processing" ||
    (validations.data?.some((run) => run.status === "pending" || run.status === "running") ?? false);
  const socket = useTestStatus(testId, Boolean(test.data) && hasOpenWork);

  const validate = useMutation({
    mutationFn: () => requestValidation(testId),
    onSuccess: () => {
      toast("Checker run queued.", "success");
      void queryClient.invalidateQueries({ queryKey: ["validations", testId] });
    },
    onError: setActionError,
  });

  const exportZip = useMutation({
    mutationFn: () => downloadExport(testId, test.data?.name ?? `test-${testId}`),
    onError: setActionError,
  });

  if (test.isPending) return <Spinner label="Loading test case" />;
  if (test.error) {
    return (
      <div className="space-y-4">
        <ErrorBanner error={test.error} />
        <Link to="/tests" className="text-sm text-accent hover:underline">
          ← Back to test cases
        </Link>
      </div>
    );
  }

  const data = test.data as TestCase;
  const notParsed = data.status !== "parsed";

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <Link to="/tests" className="text-sm text-ink-muted hover:text-ink">
            ← Test cases
          </Link>
          <h1 className="mt-1 flex items-center gap-3 text-lg font-semibold tracking-tight">
            {data.name}
            <TestStatusBadge status={data.status} />
          </h1>
        </div>

        <div className="flex flex-wrap gap-2">
          {can("test:validate") && (
            <Button
              variant="primary"
              onClick={() => validate.mutate()}
              loading={validate.isPending}
              disabled={notParsed}
              title={notParsed ? "Only a parsed test case can be validated" : undefined}
            >
              Run checker
            </Button>
          )}
          {can("test:export") && (
            <Button
              onClick={() => exportZip.mutate()}
              loading={exportZip.isPending}
              disabled={notParsed}
              title={notParsed ? "Only a parsed test case can be exported" : undefined}
            >
              Download .zip
            </Button>
          )}
        </div>
      </div>

      <ErrorBanner error={actionError} />

      {hasOpenWork && (
        <p className="text-xs text-ink-muted">
          {socket.state === "live"
            ? "Live: status updates stream in over the WebSocket. Parsing can take minutes — silence is normal."
            : socket.state === "connecting"
              ? "Connecting to the status stream…"
              : (socket.note ?? "Status stream closed.")}
        </p>
      )}

      {data.status === "error" && data.error_message && (
        <div className="rounded-md border border-red-500/40 bg-red-500/10 px-3 py-2 text-sm text-red-700 dark:text-red-300">
          <strong className="font-medium">Parsing failed:</strong> {data.error_message}
        </div>
      )}

      <div className="grid gap-4 lg:grid-cols-3">
        <Card className="lg:col-span-2">
          <CardHeader title="Overview" />
          <dl className="grid grid-cols-2 gap-x-6 gap-y-3 p-4 text-sm sm:grid-cols-3">
            <Detail label="Platform" value={data.platform.mmu_family} />
            <Detail label="Page size" value={`${data.platform.page_size} B`} />
            <Detail label="Uploaded by" value={<UserChip user={data.uploaded_by} />} />
            <Detail label="Uploaded at" value={formatDateTime(data.uploaded_at)} />
            <Detail label="Modules" value={data.module_count} />
            <Detail label="Blocks" value={data.block_count} />
            <Detail label="Kernel entries" value={data.kernel_entry_count} />
            <Detail label="User entries" value={data.user_entry_count} />
          </dl>
          {notParsed && (
            <p className="border-t border-line px-4 py-2 text-xs text-ink-muted">
              Counters stay at zero until the worker finishes parsing.
            </p>
          )}
        </Card>

        <TagPanel test={data} onError={setActionError} />
      </div>

      <ArtifactsCard testId={testId} parsed={!notParsed} onError={setActionError} />

      <Card>
        <CardHeader
          title="Validation history"
          action={
            <span className="text-xs text-ink-muted">
              {validations.data?.length ?? 0} run{validations.data?.length === 1 ? "" : "s"}
            </span>
          }
        />
        {validations.isPending ? (
          <Spinner label="Loading runs" />
        ) : validations.data && validations.data.length === 0 ? (
          <EmptyState
            title="No checker runs yet"
            hint={notParsed ? "The test case has to be parsed first." : "Run the checker to add one."}
          />
        ) : (
          <div className="divide-y divide-line/60">
            {validations.data?.map((run) => (
              <article key={run.id} className="px-4 py-3">
                <div className="flex flex-wrap items-center gap-3 text-sm">
                  <ValidationStatusBadge status={run.status} />
                  {run.status === "completed" && <VerdictBadge valid={run.valid} />}
                  {run.schema_valid === false && (
                    <span className="text-xs text-amber-700 dark:text-amber-400">
                      schema mismatch
                    </span>
                  )}
                  <span className="text-ink-muted">
                    {run.checker_version ? `checker ${run.checker_version}` : "checker version n/a"}
                  </span>
                  <span className="ml-auto text-xs text-ink-muted">
                    {formatDateTime(run.checked_at)}
                  </span>
                </div>
                {run.errors && run.errors.length > 0 && (
                  <details className="mt-2">
                    <summary className="cursor-pointer text-xs text-ink-muted">
                      {run.errors.length} checker error{run.errors.length === 1 ? "" : "s"}
                    </summary>
                    <pre className="mt-2 max-h-64 overflow-auto rounded-md bg-line/40 p-3 text-xs">
                      {JSON.stringify(run.errors, null, 2)}
                    </pre>
                  </details>
                )}
              </article>
            ))}
          </div>
        )}
      </Card>
    </div>
  );
}

function Detail({ label, value }: { label: string; value: ReactNode }) {
  return (
    <div>
      <dt className="text-xs uppercase tracking-wide text-ink-muted">{label}</dt>
      <dd className="mt-0.5 tabular-nums">{value}</dd>
    </div>
  );
}

/**
 * Tags on the test case: what is attached, and one field to add more.
 *
 * The field takes a name rather than an id from a dropdown, because a dropdown
 * dead-ends the moment the tag you want does not exist yet — and on a fresh
 * install none of them do. Typing a new name creates it and attaches it in one
 * go; typing an existing one just attaches it. Picking from the suggestions is
 * the same thing with less typing.
 */
function TagPanel({ test, onError }: { test: TestCase; onError: (error: unknown) => void }) {
  const { can } = useAuth();
  const toast = useToast();
  const queryClient = useQueryClient();
  const [draft, setDraft] = useState("");

  const tags = useQuery({ queryKey: ["tags"], queryFn: listTags, staleTime: 5 * 60_000 });

  const refresh = () => {
    void queryClient.invalidateQueries({ queryKey: ["test", test.id] });
    void queryClient.invalidateQueries({ queryKey: ["tests"] });
    void queryClient.invalidateQueries({ queryKey: ["tags"] });
  };

  const attached = new Set(test.tags.map((tag) => tag.id));
  const available = (tags.data ?? []).filter((tag) => !attached.has(tag.id));
  const mayEdit = can("test:tag");
  const mayCreate = can("tag:manage");

  const add = useMutation({
    mutationFn: async (name: string) => {
      const trimmed = name.trim();
      const byName = (list: Tag[]) =>
        list.find((tag) => tag.name.toLowerCase() === trimmed.toLowerCase());

      const known = byName(tags.data ?? []);
      if (known && attached.has(known.id)) return known;

      // Creating needs tag:manage; attaching an existing one only needs test:tag.
      const tag = known ?? (await createOrAdopt(trimmed, byName));
      await attachTag(test.id, tag.id);
      return tag;
    },
    onSuccess: (tag) => {
      setDraft("");
      toast(`Tag “${tag.name}” is on this test case.`, "success");
      refresh();
    },
    onError,
  });

  const detach = useMutation({
    mutationFn: (id: number) => detachTag(test.id, id),
    onSuccess: () => {
      toast("Tag detached.", "success");
      refresh();
    },
    onError,
  });

  const trimmed = draft.trim();
  const isNew =
    trimmed.length > 0 &&
    !(tags.data ?? []).some((tag) => tag.name.toLowerCase() === trimmed.toLowerCase());
  const tooShort = trimmed.length > 0 && trimmed.length < 2;
  const blocked = isNew && !mayCreate;

  return (
    <Card>
      <CardHeader title="Tags" />
      <div className="space-y-3 p-4">
        {test.tags.length === 0 ? (
          <p className="text-sm text-ink-muted">No tags yet.</p>
        ) : (
          <ul className="flex flex-wrap gap-2">
            {test.tags.map((tag) => (
              <li key={tag.id} className="flex items-center gap-1">
                <Badge>{tag.name}</Badge>
                {mayEdit && (
                  <button
                    type="button"
                    aria-label={`Detach ${tag.name}`}
                    disabled={detach.isPending}
                    onClick={() => detach.mutate(tag.id)}
                    className="rounded px-1 text-xs text-ink-muted hover:text-ink disabled:opacity-50"
                  >
                    ×
                  </button>
                )}
              </li>
            ))}
          </ul>
        )}

        {mayEdit && (
          <form
            className="space-y-2"
            onSubmit={(event) => {
              event.preventDefault();
              if (trimmed.length >= 2 && !blocked) add.mutate(trimmed);
            }}
          >
            <div className="flex gap-2">
              <Input
                list="known-tags"
                value={draft}
                onChange={(event) => setDraft(event.target.value)}
                placeholder={mayCreate ? "Pick or type a new tag" : "Pick a tag"}
                maxLength={50}
              />
              <datalist id="known-tags">
                {available.map((tag) => (
                  <option key={tag.id} value={tag.name} />
                ))}
              </datalist>
              <Button
                type="submit"
                variant="primary"
                loading={add.isPending}
                disabled={trimmed.length < 2 || blocked}
              >
                {isNew && mayCreate ? "Create" : "Attach"}
              </Button>
            </div>
            {tooShort ? (
              <p className="text-xs text-ink-muted">A tag name needs at least 2 characters.</p>
            ) : blocked ? (
              <p className="text-xs text-ink-muted">
                “{trimmed}” does not exist yet, and creating tags needs the tag:manage permission.
              </p>
            ) : available.length === 0 && mayCreate ? (
              <p className="text-xs text-ink-muted">
                {(tags.data ?? []).length === 0
                  ? "No tags exist yet — type a name to make the first one."
                  : "Every existing tag is already here; type a name to make a new one."}
              </p>
            ) : null}
          </form>
        )}

        {tags.error instanceof ApiError && <ErrorBanner error={tags.error} />}
      </div>
    </Card>
  );
}

/**
 * Creates a tag, or adopts the one that appeared underneath us.
 *
 * Tag names are unique service-wide, so two people naming the same thing at
 * once is an ordinary race rather than an error worth showing: whoever lost
 * simply gets the winner's tag. Any other failure is real and is re-thrown.
 */
async function createOrAdopt(
  name: string,
  byName: (list: Tag[]) => Tag | undefined,
): Promise<Tag> {
  try {
    return await createTag(name);
  } catch (error) {
    if (!(error instanceof ApiError) || error.status !== 409) throw error;
    // Straight to the API rather than through the cache: the cache is exactly
    // what was stale a moment ago.
    const adopted = byName(await listTags());
    if (!adopted) throw error;
    return adopted;
  }
}

const ARTIFACT_LABELS: Record<Artifact["kind"], string> = {
  config: "platform config",
  shared_groups: "shared groups",
  input_constraints: "input constraints",
  input_arch: "input arch",
  output_arch: "allocator output",
  output_vdefinitions: "vdefinitions",
  log: "log",
  status: "validation status",
};

/** The files the archive was broken into, each downloadable on its own. */
function ArtifactsCard({
  testId,
  parsed,
  onError,
}: {
  testId: number;
  parsed: boolean;
  onError: (error: unknown) => void;
}) {
  const { can } = useAuth();
  const mayDownload = can("test:export");

  const artifacts = useQuery({
    queryKey: ["artifacts", testId],
    queryFn: () => listArtifacts(testId),
    // Nothing is extracted before the worker finishes, and the endpoint sits
    // behind the same permission as the download it feeds.
    enabled: mayDownload && parsed,
  });

  const download = useMutation({
    mutationFn: (artifact: Artifact) => downloadArtifact(testId, artifact.id, artifact.filename),
    onError,
  });

  if (!mayDownload) return null;

  return (
    <Card>
      <CardHeader
        title="Files"
        action={<span className="text-xs text-ink-muted">{artifacts.data?.length ?? 0}</span>}
      />
      {!parsed ? (
        <EmptyState title="Nothing extracted yet" hint="Files appear once parsing finishes." />
      ) : artifacts.isPending ? (
        <Spinner label="Loading files" />
      ) : artifacts.data && artifacts.data.length === 0 ? (
        <EmptyState title="No files stored for this test case" />
      ) : (
        <ul className="divide-y divide-line/60">
          {artifacts.data?.map((artifact) => (
            <li key={artifact.id} className="flex items-center gap-3 px-4 py-2 text-sm">
              <span className="font-medium">{artifact.filename}</span>
              <Badge>{ARTIFACT_LABELS[artifact.kind] ?? artifact.kind}</Badge>
              <Button
                className="ml-auto"
                loading={download.isPending && download.variables?.id === artifact.id}
                onClick={() => download.mutate(artifact)}
              >
                Download
              </Button>
            </li>
          ))}
        </ul>
      )}
    </Card>
  );
}

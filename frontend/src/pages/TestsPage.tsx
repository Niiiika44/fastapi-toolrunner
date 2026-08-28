import { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { listTests } from "../api/tests";
import { listPlatforms } from "../api/platforms";
import { listTags } from "../api/tags";
import type { TestListQuery, TestStatus } from "../api/types";
import { useAuth } from "../auth/AuthContext";
import { useDebounced } from "../lib/useDebounced";
import { formatDateTime } from "../lib/format";
import { UserChip } from "../components/Avatar";
import {
  Badge,
  Button,
  Card,
  EmptyState,
  ErrorBanner,
  Field,
  Input,
  Select,
} from "../components/ui";
import { Spinner } from "../components/Spinner";
import { TestStatusBadge } from "../components/StatusBadge";
import { UploadDialog } from "./UploadDialog";

const STATUSES: TestStatus[] = ["pending", "processing", "parsed", "error"];
const PAGE_SIZE = 25;

export function TestsPage() {
  const { can } = useAuth();
  const queryClient = useQueryClient();

  const [name, setName] = useState("");
  const [statuses, setStatuses] = useState<TestStatus[]>([]);
  const [platformId, setPlatformId] = useState<number | "">("");
  const [tag, setTag] = useState<string>("");
  const [mine, setMine] = useState(false);
  const [offset, setOffset] = useState(0);
  const [uploadOpen, setUploadOpen] = useState(false);

  const debouncedName = useDebounced(name);

  const query: TestListQuery = useMemo(
    () => ({
      limit: PAGE_SIZE,
      offset,
      name: debouncedName || undefined,
      statuses: statuses.length ? statuses : undefined,
      platform_ids: platformId === "" ? undefined : [platformId],
      tags: tag ? [tag] : undefined,
      mine: mine || undefined,
    }),
    [offset, debouncedName, statuses, platformId, tag, mine],
  );

  const tests = useQuery({
    queryKey: ["tests", query],
    queryFn: () => listTests(query),
    // A row in PENDING or PROCESSING is waiting on a Celery worker. The status
    // WebSocket is per test case, so the list falls back to polling — but only
    // while something on the page can still change.
    refetchInterval: (result) =>
      result.state.data?.tests.some((test) => test.status === "pending" || test.status === "processing")
        ? 5000
        : false,
  });

  const platforms = useQuery({
    queryKey: ["platforms"],
    queryFn: listPlatforms,
    enabled: can("platform:read"),
    staleTime: 5 * 60_000,
  });

  const tags = useQuery({
    queryKey: ["tags"],
    queryFn: listTags,
    staleTime: 5 * 60_000,
  });

  function resetToFirstPage<T>(setter: (value: T) => void) {
    return (value: T) => {
      setOffset(0);
      setter(value);
    };
  }

  function toggleStatus(status: TestStatus) {
    setOffset(0);
    setStatuses((current) =>
      current.includes(status) ? current.filter((item) => item !== status) : [...current, status],
    );
  }

  const total = tests.data?.total ?? 0;
  const page = Math.floor(offset / PAGE_SIZE) + 1;
  const pageCount = Math.max(1, Math.ceil(total / PAGE_SIZE));

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="text-lg font-semibold tracking-tight">Test cases</h1>
        {can("test:upload") && (
          <Button variant="primary" onClick={() => setUploadOpen(true)}>
            Upload archive
          </Button>
        )}
      </div>

      <Card className="p-4">
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          <Field label="Name">
            <Input
              value={name}
              onChange={(event) => resetToFirstPage(setName)(event.target.value)}
              placeholder="substring, case-insensitive"
            />
          </Field>

          <Field label="Platform">
            <Select
              value={platformId}
              onChange={(event) =>
                resetToFirstPage(setPlatformId)(
                  event.target.value === "" ? "" : Number(event.target.value),
                )
              }
            >
              <option value="">Any</option>
              {platforms.data?.map((platform) => (
                <option key={platform.id} value={platform.id}>
                  {platform.mmu_family}
                </option>
              ))}
            </Select>
          </Field>

          <Field label="Tag">
            <Select value={tag} onChange={(event) => resetToFirstPage(setTag)(event.target.value)}>
              <option value="">Any</option>
              {tags.data?.map((item) => (
                <option key={item.id} value={item.name}>
                  {item.name}
                </option>
              ))}
            </Select>
          </Field>

          <div className="space-y-1.5">
            <span className="block text-sm font-medium text-ink">Status</span>
            <div className="flex flex-wrap gap-x-3 gap-y-1 pt-1">
              {STATUSES.map((status) => (
                <label key={status} className="flex items-center gap-1.5 text-sm text-ink-muted">
                  <input
                    type="checkbox"
                    checked={statuses.includes(status)}
                    onChange={() => toggleStatus(status)}
                  />
                  {status}
                </label>
              ))}
            </div>
          </div>
        </div>

        <div className="mt-3 flex flex-wrap items-center justify-between gap-3 border-t border-line pt-3">
          <label className="flex items-center gap-2 text-sm text-ink-muted">
            <input
              type="checkbox"
              checked={mine}
              onChange={(event) => resetToFirstPage(setMine)(event.target.checked)}
            />
            Only mine
          </label>
          <Button
            variant="ghost"
            onClick={() => {
              setName("");
              setStatuses([]);
              setPlatformId("");
              setTag("");
              setMine(false);
              setOffset(0);
            }}
          >
            Reset filters
          </Button>
        </div>
      </Card>

      <ErrorBanner error={tests.error} />

      <Card>
        {tests.isPending ? (
          <Spinner label="Loading test cases" />
        ) : tests.data && tests.data.tests.length === 0 ? (
          <EmptyState
            title="Nothing matches these filters"
            hint={total === 0 ? "Upload an archive to get started." : undefined}
          />
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full min-w-[52rem] text-sm">
              <thead className="border-b border-line text-left text-xs uppercase tracking-wide text-ink-muted">
                <tr>
                  <th className="px-4 py-2 font-medium">Name</th>
                  <th className="px-4 py-2 font-medium">Status</th>
                  <th className="px-4 py-2 font-medium">Platform</th>
                  <th className="px-4 py-2 text-right font-medium">Modules</th>
                  <th className="px-4 py-2 text-right font-medium">Blocks</th>
                  <th className="px-4 py-2 font-medium">Uploaded by</th>
                  <th className="px-4 py-2 font-medium">Uploaded</th>
                </tr>
              </thead>
              <tbody>
                {tests.data?.tests.map((test) => (
                  <tr key={test.id} className="border-b border-line/60 last:border-0 hover:bg-line/20">
                    <td className="px-4 py-2">
                      <Link to={`/tests/${test.id}`} className="font-medium text-accent hover:underline">
                        {test.name}
                      </Link>
                      {test.tags.length > 0 && (
                        <span className="ml-2 inline-flex flex-wrap gap-1 align-middle">
                          {test.tags.map((tag) => (
                            <Badge key={tag.id}>{tag.name}</Badge>
                          ))}
                        </span>
                      )}
                      {test.status === "error" && test.error_message && (
                        <p className="mt-0.5 max-w-md truncate text-xs text-red-600 dark:text-red-400">
                          {test.error_message}
                        </p>
                      )}
                    </td>
                    <td className="px-4 py-2">
                      <TestStatusBadge status={test.status} />
                    </td>
                    <td className="px-4 py-2 text-ink-muted">{test.platform.mmu_family}</td>
                    <td className="px-4 py-2 text-right tabular-nums">{test.module_count}</td>
                    <td className="px-4 py-2 text-right tabular-nums">{test.block_count}</td>
                    <td className="px-4 py-2 text-ink-muted">
                      <UserChip user={test.uploaded_by} />
                    </td>
                    <td className="px-4 py-2 text-ink-muted">{formatDateTime(test.uploaded_at)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        <div className="flex items-center justify-between border-t border-line px-4 py-3 text-sm text-ink-muted">
          <span>
            {total} test case{total === 1 ? "" : "s"} · page {page} of {pageCount}
          </span>
          <div className="flex gap-2">
            <Button disabled={offset === 0} onClick={() => setOffset(Math.max(0, offset - PAGE_SIZE))}>
              Previous
            </Button>
            <Button
              disabled={offset + PAGE_SIZE >= total}
              onClick={() => setOffset(offset + PAGE_SIZE)}
            >
              Next
            </Button>
          </div>
        </div>
      </Card>

      <UploadDialog
        open={uploadOpen}
        onClose={() => setUploadOpen(false)}
        onUploaded={() => {
          setOffset(0);
          void queryClient.invalidateQueries({ queryKey: ["tests"] });
        }}
      />
    </div>
  );
}

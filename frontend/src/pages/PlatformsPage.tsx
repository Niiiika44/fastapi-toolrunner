import { useQuery } from "@tanstack/react-query";
import { listPlatforms } from "../api/platforms";
import { formatDateTime } from "../lib/format";
import { Card, CardHeader, EmptyState, ErrorBanner } from "../components/ui";
import { Spinner } from "../components/Spinner";

export function PlatformsPage() {
  const platforms = useQuery({ queryKey: ["platforms"], queryFn: listPlatforms });

  return (
    <div className="space-y-4">
      <h1 className="text-lg font-semibold tracking-tight">Platforms</h1>
      <p className="text-sm text-ink-muted">
        Platforms are created implicitly: the first upload that introduces an MMU family becomes
        the platform every later test case for that family is filed under.
      </p>

      <ErrorBanner error={platforms.error} />

      {platforms.isPending ? (
        <Spinner label="Loading platforms" />
      ) : platforms.data && platforms.data.length === 0 ? (
        <Card>
          <EmptyState title="No platforms yet" hint="Upload a test case to create one." />
        </Card>
      ) : (
        <div className="grid gap-4 md:grid-cols-2">
          {platforms.data?.map((platform) => (
            <Card key={platform.id}>
              <CardHeader
                title={platform.mmu_family}
                action={
                  <span className="text-xs text-ink-muted">
                    first seen {formatDateTime(platform.created_at)}
                  </span>
                }
              />
              <div className="p-4 text-sm">
                <p className="text-ink-muted">
                  Page size: <span className="tabular-nums text-ink">{platform.page_size} B</span>
                </p>
              </div>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}

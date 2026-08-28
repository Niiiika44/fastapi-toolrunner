import { useState, type FormEvent } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { createTag, deleteTag, listTags } from "../api/tags";
import { Button, Card, CardHeader, EmptyState, ErrorBanner, Input } from "../components/ui";
import { Spinner } from "../components/Spinner";
import { useToast } from "../components/Toast";

export function TagsPage() {
  const queryClient = useQueryClient();
  const toast = useToast();
  const [name, setName] = useState("");
  const [error, setError] = useState<unknown>(null);

  const tags = useQuery({ queryKey: ["tags"], queryFn: listTags });

  const invalidate = () => queryClient.invalidateQueries({ queryKey: ["tags"] });

  const create = useMutation({
    mutationFn: () => createTag(name.trim()),
    onSuccess: () => {
      setName("");
      setError(null);
      toast("Tag created.", "success");
      void invalidate();
    },
    onError: setError,
  });

  const remove = useMutation({
    mutationFn: (tagId: number) => deleteTag(tagId),
    onSuccess: () => {
      toast("Tag deleted.", "success");
      void invalidate();
    },
    onError: setError,
  });

  function onSubmit(event: FormEvent) {
    event.preventDefault();
    if (name.trim().length >= 2) create.mutate();
  }

  return (
    <div className="mx-auto max-w-2xl space-y-4">
      <h1 className="text-lg font-semibold tracking-tight">Tags</h1>

      <Card className="p-4">
        <form onSubmit={onSubmit} className="flex gap-2">
          <Input
            value={name}
            onChange={(event) => setName(event.target.value)}
            placeholder="New tag name"
            minLength={2}
            maxLength={50}
            required
          />
          <Button type="submit" variant="primary" loading={create.isPending}>
            Create
          </Button>
        </form>
        <p className="mt-2 text-xs text-ink-muted">
          Names are unique across the service, 2 to 50 characters.
        </p>
      </Card>

      <ErrorBanner error={error} />

      <Card>
        <CardHeader title="All tags" />
        {tags.isPending ? (
          <Spinner label="Loading tags" />
        ) : tags.data && tags.data.length === 0 ? (
          <EmptyState title="No tags yet" />
        ) : (
          <ul className="divide-y divide-line/60">
            {tags.data?.map((tag) => (
              <li key={tag.id} className="flex items-center justify-between px-4 py-2 text-sm">
                <span>{tag.name}</span>
                <Button
                  variant="danger"
                  loading={remove.isPending && remove.variables === tag.id}
                  onClick={() => {
                    // Deleting a tag detaches it from every test case that carries it.
                    if (window.confirm(`Delete the tag “${tag.name}”?`)) remove.mutate(tag.id);
                  }}
                >
                  Delete
                </Button>
              </li>
            ))}
          </ul>
        )}
      </Card>
    </div>
  );
}

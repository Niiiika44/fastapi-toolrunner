import { api } from "./client";
import type { Tag } from "./types";

export function listTags(): Promise<Tag[]> {
  return api.get<Tag[]>("/tags");
}

export function createTag(name: string): Promise<Tag> {
  return api.post<Tag>("/tags", { name });
}

export function deleteTag(tagId: number): Promise<void> {
  return api.delete<void>(`/tags/${tagId}`);
}

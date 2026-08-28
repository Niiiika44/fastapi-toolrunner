import { api } from "./client";
import type { Platform } from "./types";

export function listPlatforms(): Promise<Platform[]> {
  return api.get<Platform[]>("/platforms");
}

export function getPlatform(platformId: number): Promise<Platform> {
  return api.get<Platform>(`/platforms/${platformId}`);
}

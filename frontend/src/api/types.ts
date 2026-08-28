/**
 * Mirrors the Pydantic schemas of the backend. Kept hand-written on purpose:
 * the surface is small and an explicit mirror makes a contract drift show up as
 * a type error instead of `any` silently spreading through the app.
 *
 * Source of truth: the schemas.py and enums.py of each backend package.
 */

export type TestStatus = "pending" | "processing" | "parsed" | "error";
export type ValidationStatus = "pending" | "running" | "completed" | "failed";
export type JobTitle = "developer" | "tester" | "analyst" | "manager" | "other";

/** app/auth/enums.py: Permission */
export const PERMISSIONS = [
  "tag:manage",
  "platform:read",
  "test:read",
  "test:upload",
  "test:validate",
  "test:export",
  "test:tag",
  "user:read_any",
  "user:update_any",
  "user:delete_any",
] as const;
export type Permission = (typeof PERMISSIONS)[number];

export interface TokenResponse {
  access_token: string;
  token_type: string;
}

export interface User {
  id: string;
  email: string;
  first_name: string;
  last_name: string;
  job_title: JobTitle;
  is_superuser: boolean;
  requested_job_title: JobTitle | null;
  /**
   * Link to the avatar, or null when the user has none. Same origin, so <img>
   * just loads it; the ?v= changes whenever the picture does.
   */
  avatar_url: string | null;
  /**
   * Everything this account may actually do — role baseline plus individual
   * grants. Only GET /users/me carries it, which is why it is optional: a user
   * from a listing is the same shape minus this field.
   */
  permissions?: Permission[];
}

export interface UserPermissionGrant {
  permission: Permission;
  granted_at: string;
}

export interface Uploader {
  id: string;
  email: string;
  first_name: string;
  last_name: string;
  /** Same field as on User, so a list of test cases can show faces. */
  avatar_url: string | null;
}

export interface PlatformRef {
  mmu_family: string;
  page_size: number;
}

export interface Platform extends PlatformRef {
  id: number;
  config: Record<string, unknown> | null;
  created_at: string;
}

export interface TestCase {
  id: number;
  name: string;
  status: TestStatus;
  error_message: string | null;
  uploaded_at: string;
  module_count: number;
  block_count: number;
  kernel_entry_count: number;
  user_entry_count: number;
  platform: PlatformRef;
  uploaded_by: Uploader;
  tags: Tag[];
}

export interface PaginatedTests {
  tests: TestCase[];
  total: number;
  limit: number;
  offset: number;
}

export interface Validation {
  id: number;
  test_id: number;
  status: ValidationStatus;
  valid: boolean | null;
  schema_valid: boolean | null;
  errors: unknown[] | null;
  checker_version: string | null;
  checked_at: string | null;
}

export interface Tag {
  id: number;
  name: string;
}

/** Role of a file inside an uploaded test case archive. */
export type ArtifactKind =
  | "config"
  | "shared_groups"
  | "input_constraints"
  | "input_arch"
  | "output_arch"
  | "output_vdefinitions"
  | "log"
  | "status";

export interface Artifact {
  id: number;
  kind: ArtifactKind;
  filename: string;
}

export interface TestListQuery {
  statuses?: TestStatus[];
  name?: string;
  platform_ids?: number[];
  tags?: string[];
  mine?: boolean;
  limit?: number;
  offset?: number;
}

/** Events pushed over wss://<host>/api/tests/{id}/status */
export interface TestStatusEvent {
  event: "test.status";
  test_id: number;
  status: TestStatus;
  error_message: string | null;
  ts: string;
}

export interface ValidationStatusEvent {
  event: "validation.status";
  test_id: number;
  validation_id: number;
  status: ValidationStatus;
  valid: boolean | null;
  ts: string;
}

export type StatusEvent = TestStatusEvent | ValidationStatusEvent;

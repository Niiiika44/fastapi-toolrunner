import { API_BASE, api, getToken, toQueryString } from "./client";
import { ApiError } from "./client";
import type { Artifact, PaginatedTests, TestCase, TestListQuery, Validation } from "./types";

export function listTests(query: TestListQuery): Promise<PaginatedTests> {
  return api.get<PaginatedTests>(`/tests${toQueryString(query as Record<string, unknown>)}`);
}

export function getTest(testId: number): Promise<TestCase> {
  return api.get<TestCase>(`/tests/${testId}`);
}

export function listValidations(testId: number): Promise<Validation[]> {
  return api.get<Validation[]>(`/tests/${testId}/validations`);
}

export function requestValidation(testId: number): Promise<Validation> {
  return api.post<Validation>(`/tests/${testId}/validate`);
}

export function attachTag(testId: number, tagId: number): Promise<void> {
  return api.post<void>(`/tests/${testId}/tags/${tagId}`);
}

export function detachTag(testId: number, tagId: number): Promise<void> {
  return api.delete<void>(`/tests/${testId}/tags/${tagId}`);
}

/**
 * Uploads through XHR rather than fetch: only XHR reports upload progress, and
 * a memory test archive is large enough that a progress bar is the difference
 * between "working" and "frozen".
 *
 * Answers 202 with the test case in PENDING; the archive is parsed by a worker.
 */
export function uploadTest(
  file: File,
  onProgress?: (percent: number) => void,
  signal?: AbortSignal,
): Promise<TestCase> {
  return new Promise((resolve, reject) => {
    const form = new FormData();
    form.append("file", file);

    const xhr = new XMLHttpRequest();
    xhr.open("POST", `${API_BASE}/tests/upload`);
    const token = getToken();
    if (token) xhr.setRequestHeader("Authorization", `Bearer ${token}`);

    xhr.upload.onprogress = (event) => {
      if (event.lengthComputable && onProgress) {
        onProgress(Math.round((event.loaded / event.total) * 100));
      }
    };

    xhr.onload = () => {
      let payload: unknown = null;
      try {
        payload = JSON.parse(xhr.responseText);
      } catch {
        payload = null;
      }
      if (xhr.status >= 200 && xhr.status < 300) {
        resolve(payload as TestCase);
        return;
      }
      const body = payload as { error?: { message?: string } } | null;
      reject(
        new ApiError(
          xhr.status,
          body?.error?.message ??
            (xhr.status === 413
              ? "The archive is larger than the server accepts (10 MB)."
              : `Upload failed with ${xhr.status}`),
          payload,
        ),
      );
    };
    xhr.onerror = () => reject(new ApiError(0, "Network error during upload"));
    xhr.onabort = () => reject(new DOMException("Upload aborted", "AbortError"));
    signal?.addEventListener("abort", () => xhr.abort());

    xhr.send(form);
  });
}

/**
 * The export endpoint needs the bearer token, so the browser cannot simply
 * follow a plain link — fetch it, then hand the blob to a synthetic anchor.
 */
export async function downloadExport(testId: number, testName: string): Promise<void> {
  const response = await fetch(`${API_BASE}/tests/${testId}/export`, {
    headers: getToken() ? { Authorization: `Bearer ${getToken()}` } : {},
  });
  if (!response.ok) {
    let message = `Export failed with ${response.status}`;
    try {
      const body = (await response.json()) as { error?: { message?: string } };
      message = body?.error?.message ?? message;
    } catch {
      /* keep the status-based message */
    }
    throw new ApiError(response.status, message);
  }

  const disposition = response.headers.get("Content-Disposition") ?? "";
  const match = /filename="?([^"]+)"?/.exec(disposition);
  saveBlob(await response.blob(), match?.[1] ?? `${testName}.zip`);
}

/** Hands a downloaded blob to the browser through a synthetic anchor. */
function saveBlob(blob: Blob, filename: string): void {
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  URL.revokeObjectURL(url);
}

export function listArtifacts(testId: number): Promise<Artifact[]> {
  return api.get<Artifact[]>(`/tests/${testId}/artifacts`);
}

/**
 * Single-artifact download. Needs the bearer token, so it goes through fetch
 * rather than a plain link.
 *
 * With the S3 backend the endpoint answers 302 to a presigned URL; fetch
 * follows it and drops the Authorization header on the cross-origin hop, which
 * is exactly what the presigned link expects.
 */
export async function downloadArtifact(
  testId: number,
  artifactId: number,
  filename: string,
): Promise<void> {
  const response = await fetch(`${API_BASE}/tests/${testId}/artifacts/${artifactId}/download`, {
    headers: getToken() ? { Authorization: `Bearer ${getToken()}` } : {},
  });
  if (!response.ok) {
    throw new ApiError(response.status, `Could not download ${filename}`);
  }
  saveBlob(await response.blob(), filename);
}

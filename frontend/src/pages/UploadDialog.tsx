import { useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { uploadTest } from "../api/tests";
import { formatBytes } from "../lib/format";
import { Button, ErrorBanner } from "../components/ui";
import { Modal } from "../components/Modal";
import { useToast } from "../components/Toast";

/** nginx caps request bodies at 10m (deploy/nginx/nginx.conf). */
const MAX_UPLOAD_BYTES = 10 * 1024 * 1024;

export function UploadDialog({
  open,
  onClose,
  onUploaded,
}: {
  open: boolean;
  onClose: () => void;
  onUploaded: () => void;
}) {
  const navigate = useNavigate();
  const toast = useToast();
  const inputRef = useRef<HTMLInputElement>(null);
  const [file, setFile] = useState<File | null>(null);
  const [dragging, setDragging] = useState(false);
  const [progress, setProgress] = useState<number | null>(null);
  const [error, setError] = useState<unknown>(null);

  const tooLarge = file !== null && file.size > MAX_UPLOAD_BYTES;

  function reset() {
    setFile(null);
    setProgress(null);
    setError(null);
    setDragging(false);
  }

  function pick(chosen: File | undefined) {
    if (!chosen) return;
    setError(null);
    setFile(chosen);
  }

  async function submit() {
    if (!file || tooLarge) return;
    setError(null);
    setProgress(0);
    try {
      const test = await uploadTest(file, setProgress);
      // 202: the row exists in PENDING and a worker takes it from here, so the
      // useful next step is the detail page, where the status streams in live.
      toast(`Upload accepted — “${test.name}” is queued for parsing.`, "success");
      onUploaded();
      reset();
      onClose();
      navigate(`/tests/${test.id}`);
    } catch (cause) {
      setError(cause);
      setProgress(null);
    }
  }

  return (
    <Modal
      open={open}
      title="Upload a test case archive"
      onClose={() => {
        if (progress !== null) return; // do not drop an upload in flight
        reset();
        onClose();
      }}
    >
      <div className="space-y-4">
        <div
          onDragOver={(event) => {
            event.preventDefault();
            setDragging(true);
          }}
          onDragLeave={() => setDragging(false)}
          onDrop={(event) => {
            event.preventDefault();
            setDragging(false);
            pick(event.dataTransfer.files[0]);
          }}
          onClick={() => inputRef.current?.click()}
          className={`cursor-pointer rounded-lg border border-dashed px-4 py-8 text-center text-sm transition ${
            dragging ? "border-accent bg-accent/5" : "border-line text-ink-muted"
          }`}
        >
          <input
            ref={inputRef}
            type="file"
            accept=".zip,application/zip"
            hidden
            onChange={(event) => pick(event.target.files?.[0])}
          />
          {file ? (
            <>
              <p className="font-medium text-ink">{file.name}</p>
              <p className="mt-1">{formatBytes(file.size)}</p>
            </>
          ) : (
            <>
              <p className="font-medium text-ink">Drop a .zip here</p>
              <p className="mt-1">or click to choose a file</p>
            </>
          )}
        </div>

        {tooLarge && (
          <p className="text-sm text-red-600 dark:text-red-400">
            {formatBytes(file.size)} exceeds the {formatBytes(MAX_UPLOAD_BYTES)} limit the server
            accepts.
          </p>
        )}

        {progress !== null && (
          <div className="space-y-1">
            <div className="h-1.5 w-full overflow-hidden rounded-full bg-line">
              <div
                className="h-full bg-accent transition-[width]"
                style={{ width: `${progress}%` }}
              />
            </div>
            <p className="text-xs text-ink-muted">
              {progress < 100 ? `Uploading ${progress}%` : "Waiting for the server to accept it…"}
            </p>
          </div>
        )}

        <ErrorBanner error={error} />

        <p className="text-xs text-ink-muted">
          Only <code>memin.yaml</code> is read straight away, to resolve the platform. The rest of
          the archive is parsed by a background worker, so the test case appears as{" "}
          <strong>pending</strong> first.
        </p>

        <div className="flex justify-end gap-2">
          <Button
            onClick={() => {
              reset();
              onClose();
            }}
            disabled={progress !== null}
          >
            Cancel
          </Button>
          <Button
            variant="primary"
            onClick={submit}
            disabled={!file || tooLarge}
            loading={progress !== null}
          >
            Upload
          </Button>
        </div>
      </div>
    </Modal>
  );
}

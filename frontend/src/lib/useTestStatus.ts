import { useEffect, useRef, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { WS_CLOSE_REASON, isTerminalCloseCode, openStatusSocket } from "../api/ws";
import type { StatusEvent, TestCase } from "../api/types";
import { useAuth } from "../auth/AuthContext";

export type SocketState = "connecting" | "live" | "closed";

interface Result {
  state: SocketState;
  /** Why the socket closed, when it closed for a reason worth showing. */
  note: string | null;
}

/**
 * Subscribes to the status WebSocket of one test case and folds the events into
 * the React Query cache, so every component reading the test case updates at
 * once and no polling is needed while the socket is up.
 *
 * Reconnects with a capped backoff on transport-level closes only: 4401/4403/
 * 4404/1008 are verdicts, and retrying them just burns the per-user connection
 * budget (WS_MAX_CONNECTIONS_PER_USER, default 5).
 */
export function useTestStatus(testId: number, enabled: boolean): Result {
  const { token } = useAuth();
  const queryClient = useQueryClient();
  const [state, setState] = useState<SocketState>("connecting");
  const [note, setNote] = useState<string | null>(null);
  const attemptRef = useRef(0);

  useEffect(() => {
    if (!enabled || !token) return;

    let socket: WebSocket | null = null;
    let retryTimer = 0;
    let disposed = false;

    const handleEvent = (event: StatusEvent) => {
      if (event.event === "test.status") {
        queryClient.setQueryData<TestCase>(["test", testId], (current) =>
          current
            ? { ...current, status: event.status, error_message: event.error_message }
            : current,
        );
        // Counters are filled in by the worker at the same commit as PARSED,
        // and they do not travel in the event — refetch to pick them up.
        if (event.status === "parsed" || event.status === "error") {
          void queryClient.invalidateQueries({ queryKey: ["test", testId] });
          void queryClient.invalidateQueries({ queryKey: ["tests"] });
        }
      } else {
        void queryClient.invalidateQueries({ queryKey: ["validations", testId] });
      }
    };

    const connect = () => {
      if (disposed) return;
      setState("connecting");
      socket = openStatusSocket(testId, token, {
        onOpen: () => {
          attemptRef.current = 0;
          setState("live");
          setNote(null);
        },
        onEvent: handleEvent,
        onClose: (code) => {
          if (disposed) return;
          setState("closed");
          if (isTerminalCloseCode(code)) {
            setNote(code === 1000 ? null : (WS_CLOSE_REASON[code] ?? `Closed (${code})`));
            return;
          }
          setNote(WS_CLOSE_REASON[code] ?? `Connection lost (${code})`);
          const delay = Math.min(30_000, 1000 * 2 ** attemptRef.current++);
          retryTimer = window.setTimeout(connect, delay);
        },
      });
    };

    connect();

    return () => {
      disposed = true;
      window.clearTimeout(retryTimer);
      socket?.close(1000, "component unmounted");
    };
  }, [testId, token, enabled, queryClient]);

  return { state, note };
}

import type { StatusEvent } from "./types";

/**
 * Status WebSocket (`wss://<host>/api/tests/{id}/status`).
 *
 * The browser WebSocket API cannot set headers, so the token goes through the
 * subprotocol channel the backend supports: `Sec-WebSocket-Protocol: bearer,
 * <token>` (app/memory_allocator/routers/tests_ws_routes.py).
 *
 * The channel is silent between events — parsing can take minutes — so silence
 * must never be read as a dead connection. Only a close event is.
 */

export interface StatusSocketHandlers {
  onEvent: (event: StatusEvent) => void;
  onClose?: (code: number, reason: string) => void;
  onOpen?: () => void;
}

/** Close codes the backend uses on top of the standard ones. */
export const WS_CLOSE_REASON: Record<number, string> = {
  1000: "Connection closed",
  1008: "Missing or invalid token",
  1011: "Server error",
  1013: "Too many open connections for this user",
  4401: "Token expired",
  4403: "Not enough permissions",
  4404: "Test case not found",
};

/** A close the client should not retry: the outcome will not change by itself. */
export function isTerminalCloseCode(code: number): boolean {
  return code === 1000 || code === 1008 || code === 4401 || code === 4403 || code === 4404;
}

export function openStatusSocket(
  testId: number,
  token: string,
  handlers: StatusSocketHandlers,
): WebSocket {
  const scheme = window.location.protocol === "https:" ? "wss" : "ws";
  const url = `${scheme}://${window.location.host}/api/tests/${testId}/status`;

  const socket = new WebSocket(url, ["bearer", token]);

  socket.onopen = () => handlers.onOpen?.();
  socket.onmessage = (message) => {
    try {
      handlers.onEvent(JSON.parse(message.data as string) as StatusEvent);
    } catch {
      /* a frame we cannot parse is not worth tearing the socket down for */
    }
  };
  socket.onclose = (event) => handlers.onClose?.(event.code, event.reason);

  return socket;
}

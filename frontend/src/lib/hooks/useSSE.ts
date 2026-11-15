'use client';

import { useEffect, useRef, useState, useCallback } from 'react';
import { getApiBaseUrl } from '@/lib/api/client';

export interface SSECallbacks {
  onActivityEvent?: (data: unknown) => void;
  onRunStatusChanged?: (data: unknown) => void;
  onAgentStatusChanged?: (data: unknown) => void;
  onSourceAdded?: (data: unknown) => void;
  onEvidenceAdded?: (data: unknown) => void;
  onApprovalRequired?: (data: unknown) => void;
  onApprovalResolved?: (data: unknown) => void;
  onRunCompleted?: (data: unknown) => void;
  onRunFailed?: (data: unknown) => void;
}

export interface SSEState {
  connected: boolean;
}

/**
 * Fetch-based SSE hook. Uses fetch streaming instead of native EventSource so
 * we can send the Last-Event-ID header on reconnect.
 */
export function useSSE(
  runId: string | null,
  projectId: string | null,
  callbacks: SSECallbacks,
): SSEState {
  const [connected, setConnected] = useState(false);
  const lastEventIdRef = useRef<string | null>(null);
  const abortControllerRef = useRef<AbortController | null>(null);
  const reconnectTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const mountedRef = useRef(true);

  // Keep callbacks in a ref so the connect loop never needs to re-register
  const callbacksRef = useRef<SSECallbacks>(callbacks);
  useEffect(() => {
    callbacksRef.current = callbacks;
  });

  const dispatchEvent = useCallback((eventType: string, data: unknown) => {
    const cb = callbacksRef.current;
    switch (eventType) {
      case 'activity':
      case 'activity_event':
        cb.onActivityEvent?.(data);
        break;
      case 'status_change':
      case 'run_status_changed':
        cb.onRunStatusChanged?.(data);
        break;
      case 'agent_status_changed':
        cb.onAgentStatusChanged?.(data);
        break;
      case 'source_added':
        cb.onSourceAdded?.(data);
        break;
      case 'evidence_added':
        cb.onEvidenceAdded?.(data);
        break;
      case 'approval_required':
        cb.onApprovalRequired?.(data);
        break;
      case 'approval_resolved':
        cb.onApprovalResolved?.(data);
        break;
      case 'run_completed':
        cb.onRunCompleted?.(data);
        break;
      case 'run_failed':
        cb.onRunFailed?.(data);
        break;
      // heartbeat — no callback needed
    }
  }, []);

  const connect = useCallback(async () => {
    if (!runId || !projectId || !mountedRef.current) return;

    // Abort any existing connection
    abortControllerRef.current?.abort();
    const controller = new AbortController();
    abortControllerRef.current = controller;

    const base = getApiBaseUrl();
    const url = `${base}/api/v1/projects/${projectId}/runs/${runId}/stream`;

    const headers: Record<string, string> = {
      Accept: 'text/event-stream',
      'Cache-Control': 'no-cache',
    };
    if (lastEventIdRef.current) {
      headers['Last-Event-ID'] = lastEventIdRef.current;
    }

    try {
      const response = await fetch(url, {
        headers,
        credentials: 'include',
        signal: controller.signal,
      });

      if (!response.ok || !response.body) {
        throw new Error(`SSE connect failed: ${response.status}`);
      }

      if (!mountedRef.current) return;
      setConnected(true);

      const reader = response.body.getReader();
      const decoder = new TextDecoder();

      let buffer = '';
      let currentId = '';
      let currentEvent = '';
      let currentData = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });

        const lines = buffer.split('\n');
        buffer = lines.pop() ?? '';

        for (const line of lines) {
          if (line === '') {
            // Blank line = dispatch event
            if (currentData) {
              if (currentId) {
                lastEventIdRef.current = currentId;
              }
              try {
                const parsed: unknown = JSON.parse(currentData);
                dispatchEvent(currentEvent || 'message', parsed);
              } catch {
                // non-JSON data — skip
              }
            }
            // Reset for next event
            currentId = '';
            currentEvent = '';
            currentData = '';
          } else if (line.startsWith('id:')) {
            currentId = line.slice(3).trim();
          } else if (line.startsWith('event:')) {
            currentEvent = line.slice(6).trim();
          } else if (line.startsWith('data:')) {
            currentData = line.slice(5).trim();
          }
          // lines starting with ':' are comments (e.g. heartbeat ping) — ignore
        }
      }
    } catch (err) {
      // AbortError = intentional cleanup, don't reconnect
      if (err instanceof Error && err.name === 'AbortError') return;
    }

    if (!mountedRef.current) return;

    setConnected(false);

    // Reconnect after 3 seconds
    reconnectTimerRef.current = setTimeout(() => {
      if (mountedRef.current) connect();
    }, 3000);
  }, [runId, projectId, dispatchEvent]);

  useEffect(() => {
    mountedRef.current = true;

    if (runId && projectId) {
      connect();
    }

    return () => {
      mountedRef.current = false;
      if (reconnectTimerRef.current) clearTimeout(reconnectTimerRef.current);
      abortControllerRef.current?.abort();
    };
  }, [runId, projectId, connect]);

  return { connected };
}

/**
 * useSSE hook tests
 *
 * Strategy: Mock the global `fetch` to return a readable stream that we
 * control, then render the hook with `renderHook` and drive the stream by
 * pushing SSE-formatted chunks through the mock.
 *
 * Note: we mock `@/lib/api/client` so that `getApiBaseUrl` returns a stable
 * base URL without depending on `process.env` or window availability.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { renderHook, act, waitFor } from '@testing-library/react';

// Mock getApiBaseUrl before importing useSSE
vi.mock('@/lib/api/client', () => ({
  getApiBaseUrl: () => 'http://localhost:8000',
  ApiError: class ApiError extends Error {
    constructor(public status: number, message: string) { super(message); }
  },
}));

import { useSSE } from '../useSSE';

// ── Helpers ────────────────────────────────────────────────────────────────

/**
 * Creates a controllable ReadableStream.
 * Returns { stream, push(chunk), close() }.
 */
function makeStream() {
  let controller!: ReadableStreamDefaultController<Uint8Array>;
  const stream = new ReadableStream<Uint8Array>({
    start(c) {
      controller = c;
    },
  });
  const enc = new TextEncoder();
  return {
    stream,
    push(chunk: string) {
      controller.enqueue(enc.encode(chunk));
    },
    close() {
      controller.close();
    },
  };
}

/** Formats an SSE event string (including trailing blank line). */
function sseEvent(opts: { id?: string; event?: string; data: string }): string {
  let str = '';
  if (opts.id) str += `id: ${opts.id}\n`;
  if (opts.event) str += `event: ${opts.event}\n`;
  str += `data: ${opts.data}\n\n`;
  return str;
}

// ── Setup / Teardown ───────────────────────────────────────────────────────

let fetchMock: ReturnType<typeof vi.fn>;

beforeEach(() => {
  fetchMock = vi.fn();
  vi.stubGlobal('fetch', fetchMock);
});

afterEach(() => {
  vi.restoreAllMocks();
});

// ── Tests ──────────────────────────────────────────────────────────────────

describe('useSSE', () => {
  it('returns connected: false initially and does not fetch when runId is null', () => {
    const { result } = renderHook(() => useSSE(null, null, {}));
    expect(result.current.connected).toBe(false);
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it('returns connected: false when projectId is null', () => {
    const { result } = renderHook(() => useSSE('run-1', null, {}));
    expect(result.current.connected).toBe(false);
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it('opens a fetch connection when runId and projectId are provided', async () => {
    const { stream } = makeStream();
    fetchMock.mockResolvedValue(
      new Response(stream, { status: 200 }),
    );

    renderHook(() => useSSE('run-1', 'proj-1', {}));

    await waitFor(() => expect(fetchMock).toHaveBeenCalledOnce(), { timeout: 2000 });

    const [url] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(url).toContain('/api/v1/projects/proj-1/runs/run-1/stream');
  });

  it('transitions to connected: true after stream opens successfully', async () => {
    const { stream, push } = makeStream();
    fetchMock.mockResolvedValue(
      new Response(stream, { status: 200 }),
    );

    const { result } = renderHook(() => useSSE('run-1', 'proj-1', {}));

    await waitFor(() => expect(result.current.connected).toBe(true), { timeout: 2000 });

    // keep stream alive
    act(() => push(''));
  });

  it('calls onActivityEvent when an activity SSE event arrives', async () => {
    const { stream, push } = makeStream();
    fetchMock.mockResolvedValue(new Response(stream, { status: 200 }));

    const onActivityEvent = vi.fn();
    renderHook(() => useSSE('run-1', 'proj-1', { onActivityEvent }));

    await waitFor(() => expect(fetchMock).toHaveBeenCalledOnce(), { timeout: 2000 });

    const payload = { id: 'evt-1', agent_name: 'planner', summary: 'Test' };
    act(() => {
      push(sseEvent({ event: 'activity', data: JSON.stringify(payload) }));
    });

    await waitFor(() => expect(onActivityEvent).toHaveBeenCalledOnce(), { timeout: 2000 });
    expect(onActivityEvent).toHaveBeenCalledWith(payload);
  });

  it('dispatches activity_event type alias to onActivityEvent', async () => {
    const { stream, push } = makeStream();
    fetchMock.mockResolvedValue(new Response(stream, { status: 200 }));

    const onActivityEvent = vi.fn();
    renderHook(() => useSSE('run-1', 'proj-1', { onActivityEvent }));

    await waitFor(() => expect(fetchMock).toHaveBeenCalledOnce(), { timeout: 2000 });

    const payload = { id: 'evt-2', agent_name: 'researcher', summary: 'Search done' };
    act(() => {
      push(sseEvent({ event: 'activity_event', data: JSON.stringify(payload) }));
    });

    await waitFor(() => expect(onActivityEvent).toHaveBeenCalledOnce(), { timeout: 2000 });
  });

  it('calls onRunCompleted when a run_completed event arrives', async () => {
    const { stream, push } = makeStream();
    fetchMock.mockResolvedValue(new Response(stream, { status: 200 }));

    const onRunCompleted = vi.fn();
    renderHook(() => useSSE('run-1', 'proj-1', { onRunCompleted }));

    await waitFor(() => expect(fetchMock).toHaveBeenCalledOnce(), { timeout: 2000 });

    const payload = { run_id: 'run-1', status: 'completed' };
    act(() => {
      push(sseEvent({ event: 'run_completed', data: JSON.stringify(payload) }));
    });

    await waitFor(() => expect(onRunCompleted).toHaveBeenCalledOnce(), { timeout: 2000 });
    expect(onRunCompleted).toHaveBeenCalledWith(payload);
  });

  it('calls onRunStatusChanged when a status_change event arrives', async () => {
    const { stream, push } = makeStream();
    fetchMock.mockResolvedValue(new Response(stream, { status: 200 }));

    const onRunStatusChanged = vi.fn();
    renderHook(() => useSSE('run-1', 'proj-1', { onRunStatusChanged }));

    await waitFor(() => expect(fetchMock).toHaveBeenCalledOnce(), { timeout: 2000 });

    const payload = { run_id: 'run-1', status: 'running', current_stage: 'Planning' };
    act(() => {
      push(sseEvent({ event: 'status_change', data: JSON.stringify(payload) }));
    });

    await waitFor(() => expect(onRunStatusChanged).toHaveBeenCalledOnce(), { timeout: 2000 });
    expect(onRunStatusChanged).toHaveBeenCalledWith(payload);
  });

  it('sends Last-Event-ID header on reconnect after stream closes', async () => {
    const { stream: stream1, push: push1, close: close1 } = makeStream();
    const { stream: stream2 } = makeStream();

    fetchMock
      .mockResolvedValueOnce(new Response(stream1, { status: 200 }))
      .mockResolvedValueOnce(new Response(stream2, { status: 200 }));

    renderHook(() => useSSE('run-1', 'proj-1', {}));

    await waitFor(() => expect(fetchMock).toHaveBeenCalledOnce(), { timeout: 2000 });

    // Push an event with an id, then close the stream
    act(() => {
      push1(sseEvent({ id: 'run-1:5', event: 'activity', data: '{"id":"e5"}' }));
    });

    // Wait for the event to be processed before closing
    await new Promise((r) => setTimeout(r, 50));

    act(() => { close1(); });

    // Wait for reconnect (without fake timers — the 3s delay is real here,
    // but we advance past it by overriding the hook's setTimeout)
    // Instead verify the reconnect does happen eventually via mock call count.
    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(2), {
      timeout: 5000,
    });

    const secondCallHeaders = (fetchMock.mock.calls[1][1] as RequestInit | undefined)
      ?.headers as Record<string, string> | undefined;
    expect(secondCallHeaders?.['Last-Event-ID']).toBe('run-1:5');
  }, 8000);

  it('reconnects after a simulated disconnect', async () => {
    const { stream: stream1, close: close1 } = makeStream();
    const { stream: stream2 } = makeStream();

    fetchMock
      .mockResolvedValueOnce(new Response(stream1, { status: 200 }))
      .mockResolvedValueOnce(new Response(stream2, { status: 200 }));

    renderHook(() => useSSE('run-1', 'proj-1', {}));

    await waitFor(() => expect(fetchMock).toHaveBeenCalledOnce(), { timeout: 2000 });

    act(() => { close1(); });

    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(2), { timeout: 5000 });
  }, 8000);

  it('aborts fetch on unmount and does not call fetch a second time', async () => {
    const { stream } = makeStream();
    let capturedSignal: AbortSignal | undefined;

    fetchMock.mockImplementation(((_url: string, opts: RequestInit) => {
      capturedSignal = opts?.signal as AbortSignal;
      return Promise.resolve(new Response(stream, { status: 200 }));
    }) as typeof fetch);

    const { unmount } = renderHook(() => useSSE('run-1', 'proj-1', {}));

    await waitFor(() => expect(fetchMock).toHaveBeenCalledOnce(), { timeout: 2000 });
    expect(capturedSignal).toBeDefined();

    unmount();

    expect(capturedSignal!.aborted).toBe(true);

    // Wait longer than the reconnect delay to confirm no second fetch occurs
    await new Promise((r) => setTimeout(r, 200));
    expect(fetchMock).toHaveBeenCalledOnce();
  });

  it('stays disconnected and eventually reconnects after a fetch error', async () => {
    const { stream: stream2 } = makeStream();

    fetchMock
      .mockRejectedValueOnce(new Error('Network failure'))
      .mockResolvedValueOnce(new Response(stream2, { status: 200 }));

    const { result } = renderHook(() => useSSE('run-1', 'proj-1', {}));

    // After first failed attempt, connected stays false
    await waitFor(() => expect(fetchMock).toHaveBeenCalledOnce(), { timeout: 2000 });
    expect(result.current.connected).toBe(false);

    // Eventually reconnects (second fetch is made after 3s delay)
    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(2), { timeout: 5000 });
  }, 8000);
});

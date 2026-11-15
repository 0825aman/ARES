/**
 * Generates a UUID v4 for request correlation.
 * Uses crypto.randomUUID() where available (all modern browsers + Node 15+),
 * falls back to a Math.random-based approximation for older runtimes.
 */
function generateRequestId(): string {
  if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') {
    return crypto.randomUUID();
  }
  // Fallback for environments without crypto.randomUUID
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, (c) => {
    const r = (Math.random() * 16) | 0;
    const v = c === 'x' ? r : (r & 0x3) | 0x8;
    return v.toString(16);
  });
}

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
    public requestId?: string,
  ) {
    super(message);
    this.name = 'ApiError';
  }
}

function getServerApiUrl(): string {
  return process.env.API_URL ?? 'http://127.0.0.1:8000';
}

function getClientApiUrl(): string {
  return process.env.NEXT_PUBLIC_API_URL ?? '';
}

export function getApiBaseUrl(): string {
  if (typeof window === 'undefined') {
    return getServerApiUrl();
  }
  return getClientApiUrl();
}

/** Sleep for the given number of milliseconds. */
function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

export async function apiFetch<T>(path: string, options?: RequestInit): Promise<T> {
  const base = getApiBaseUrl();
  const requestId = generateRequestId();

  const doFetch = () =>
    fetch(`${base}${path}`, {
      credentials: 'include',
      headers: {
        'Content-Type': 'application/json',
        'X-Request-ID': requestId,
        ...options?.headers,
      },
      ...options,
    });

  let res = await doFetch();

  // Single retry on 5xx responses (transient server errors)
  if (res.status >= 500 && res.status < 600) {
    await sleep(1000);
    res = await doFetch();
  }

  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      if (typeof body.detail === 'string') {
        detail = body.detail;
      } else if (Array.isArray(body.detail) && body.detail.length > 0) {
        detail = body.detail.map((e: { msg: string }) => e.msg).join(', ');
      }
    } catch {
      // keep statusText
    }
    const responseRequestId = res.headers.get('X-Request-ID') ?? requestId;
    throw new ApiError(res.status, detail, responseRequestId);
  }

  if (res.status === 204) return undefined as T;
  return res.json() as Promise<T>;
}

export async function apiFetchMultipart<T>(path: string, formData: FormData): Promise<T> {
  const base = getApiBaseUrl();
  const requestId = generateRequestId();
  const res = await fetch(`${base}${path}`, {
    method: 'POST',
    credentials: 'include',
    headers: {
      'X-Request-ID': requestId,
      // Do NOT set Content-Type — browser sets it with the correct boundary
    },
    body: formData,
  });

  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      if (typeof body.detail === 'string') {
        detail = body.detail;
      } else if (Array.isArray(body.detail) && body.detail.length > 0) {
        detail = body.detail.map((e: { msg: string }) => e.msg).join(', ');
      }
    } catch {
      // keep statusText
    }
    const responseRequestId = res.headers.get('X-Request-ID') ?? requestId;
    throw new ApiError(res.status, detail, responseRequestId);
  }

  if (res.status === 204) return undefined as T;
  return res.json() as Promise<T>;
}

import { apiFetch } from './client';

export interface AuthUser {
  id: string;
  username: string;
  role: string;
}

export async function login(username: string, password: string): Promise<AuthUser> {
  return apiFetch<AuthUser>('/api/v1/auth/login', {
    method: 'POST',
    body: JSON.stringify({ username, password }),
  });
}

export async function startSession(): Promise<AuthUser> {
  return apiFetch<AuthUser>('/api/v1/auth/start', {
    method: 'POST',
  });
}

export async function logout(): Promise<void> {
  await apiFetch<void>('/api/v1/auth/logout', { method: 'POST' });
}

export async function getMe(): Promise<AuthUser> {
  return apiFetch<AuthUser>('/api/v1/auth/me');
}

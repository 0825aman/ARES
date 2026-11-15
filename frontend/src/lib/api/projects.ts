import { apiFetch } from './client';
import type {
  Project,
  ProjectListResponse,
  ProjectSummaryResponse,
  CreateProjectInput,
  UpdateProjectInput,
} from '@/lib/types/project';

export async function getProjects(params?: {
  limit?: number;
  offset?: number;
  status?: string;
}): Promise<ProjectListResponse> {
  const query = new URLSearchParams();
  if (params?.limit !== undefined) query.set('limit', String(params.limit));
  if (params?.offset !== undefined) query.set('offset', String(params.offset));
  if (params?.status) query.set('status', params.status);
  const qs = query.toString();
  return apiFetch<ProjectListResponse>(`/api/v1/projects${qs ? `?${qs}` : ''}`);
}

export async function getProject(id: string): Promise<Project> {
  return apiFetch<Project>(`/api/v1/projects/${id}`);
}

export async function createProject(data: CreateProjectInput): Promise<Project> {
  return apiFetch<Project>('/api/v1/projects', {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

export async function updateProject(id: string, data: UpdateProjectInput): Promise<Project> {
  return apiFetch<Project>(`/api/v1/projects/${id}`, {
    method: 'PATCH',
    body: JSON.stringify(data),
  });
}

export async function deleteProject(id: string): Promise<void> {
  return apiFetch<void>(`/api/v1/projects/${id}`, {
    method: 'DELETE',
  });
}

export async function getProjectSummary(): Promise<ProjectSummaryResponse> {
  return apiFetch<ProjectSummaryResponse>('/api/v1/projects/summary');
}

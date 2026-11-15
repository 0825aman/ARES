import { apiFetch, apiFetchMultipart } from './client';
import type {
  ResearchRun,
  RunListResponse,
  ResearchReport,
  DocumentUploadResponse,
  StartRunInput,
  ResearchPlan,
  AgentActivity,
  TaskListResponse,
  Source,
  SourceListResponse,
  EvidenceItem,
  EvidenceListResponse,
  ClaimListResponse,
  CriticReview,
  BibliographyResponse,
  ApprovalRequest,
  ApprovalListResponse,
  DecisionInput,
  DecisionResponse,
  ExportRecord,
  ExportListResponse,
  ExportRequest,
  ReportVersionListResponse,
} from '@/lib/types/run';

interface DocumentListResponse {
  items: Array<{
    id: string;
    original_filename: string;
    file_size_bytes: number;
    mime_type: string;
    uploaded_at: string;
    run_id: string | null;
    project_id: string;
    extraction_status: string;
  }>;
  total: number;
}

export async function getRuns(projectId: string): Promise<RunListResponse> {
  return apiFetch<RunListResponse>(`/api/v1/projects/${projectId}/runs`);
}

export async function getRun(projectId: string, runId: string): Promise<ResearchRun> {
  return apiFetch<ResearchRun>(`/api/v1/projects/${projectId}/runs/${runId}`);
}

export async function startRun(projectId: string, data: StartRunInput): Promise<ResearchRun> {
  return apiFetch<ResearchRun>(`/api/v1/projects/${projectId}/runs`, {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

export async function getReport(projectId: string, runId: string): Promise<ResearchReport> {
  return apiFetch<ResearchReport>(`/api/v1/projects/${projectId}/runs/${runId}/report`);
}

export async function uploadDocuments(
  projectId: string,
  files: File[]
): Promise<DocumentUploadResponse> {
  const formData = new FormData();
  files.forEach((file) => formData.append('files', file));
  return apiFetchMultipart<DocumentUploadResponse>(
    `/api/v1/projects/${projectId}/documents`,
    formData
  );
}

export async function listDocuments(projectId: string): Promise<DocumentListResponse> {
  return apiFetch<DocumentListResponse>(`/api/v1/projects/${projectId}/documents`);
}

export async function deleteDocument(projectId: string, documentId: string): Promise<void> {
  return apiFetch<void>(`/api/v1/projects/${projectId}/documents/${documentId}`, {
    method: 'DELETE',
  });
}

// ── Phase 3 API calls ──────────────────────────────────────────────────────

export async function getPlan(projectId: string, runId: string): Promise<ResearchPlan> {
  return apiFetch<ResearchPlan>(`/api/v1/projects/${projectId}/runs/${runId}/plan`);
}

export async function getTasks(projectId: string, runId: string): Promise<TaskListResponse> {
  return apiFetch<TaskListResponse>(`/api/v1/projects/${projectId}/runs/${runId}/tasks`);
}

export async function getActivity(
  projectId: string,
  runId: string,
  limit = 50
): Promise<AgentActivity> {
  return apiFetch<AgentActivity>(
    `/api/v1/projects/${projectId}/runs/${runId}/activity?limit=${limit}`
  );
}

// ── Phase 4 API calls ──────────────────────────────────────────────────────

export async function getSources(
  projectId: string,
  runId: string
): Promise<SourceListResponse> {
  return apiFetch<SourceListResponse>(
    `/api/v1/projects/${projectId}/runs/${runId}/sources`
  );
}

export async function getEvidence(
  projectId: string,
  runId: string
): Promise<EvidenceListResponse> {
  return apiFetch<EvidenceListResponse>(
    `/api/v1/projects/${projectId}/runs/${runId}/evidence`
  );
}

export async function getClaims(
  projectId: string,
  runId: string
): Promise<ClaimListResponse> {
  return apiFetch<ClaimListResponse>(
    `/api/v1/projects/${projectId}/runs/${runId}/claims`
  );
}

export async function getCriticReview(
  projectId: string,
  runId: string
): Promise<CriticReview> {
  return apiFetch<CriticReview>(
    `/api/v1/projects/${projectId}/runs/${runId}/review`
  );
}

export async function getCitations(
  projectId: string,
  runId: string
): Promise<BibliographyResponse> {
  return apiFetch<BibliographyResponse>(
    `/api/v1/projects/${projectId}/runs/${runId}/citations`
  );
}

// ── Phase 5 API calls ──────────────────────────────────────────────────────

export async function getSourceById(
  projectId: string,
  runId: string,
  sourceId: string
): Promise<Source> {
  return apiFetch<Source>(
    `/api/v1/projects/${projectId}/runs/${runId}/sources/${sourceId}`
  );
}

export async function getEvidenceById(
  projectId: string,
  runId: string,
  evidenceId: string
): Promise<EvidenceItem> {
  return apiFetch<EvidenceItem>(
    `/api/v1/projects/${projectId}/runs/${runId}/evidence/${evidenceId}`
  );
}

// ── Phase 5 M5.5 — Approval API calls ─────────────────────────────────────────

export async function getPendingApproval(
  projectId: string,
  runId: string
): Promise<ApprovalRequest | null> {
  return apiFetch<ApprovalRequest | null>(
    `/api/v1/projects/${projectId}/runs/${runId}/approval`
  );
}

export async function submitApprovalDecision(
  projectId: string,
  runId: string,
  approvalId: string,
  data: DecisionInput
): Promise<DecisionResponse> {
  return apiFetch<DecisionResponse>(
    `/api/v1/projects/${projectId}/runs/${runId}/approval/${approvalId}/decide`,
    {
      method: 'POST',
      body: JSON.stringify(data),
    }
  );
}

export async function listApprovals(
  projectId: string,
  runId: string
): Promise<ApprovalListResponse> {
  return apiFetch<ApprovalListResponse>(
    `/api/v1/projects/${projectId}/runs/${runId}/approvals`
  );
}

// ── Phase 5 M5.6 — Export API calls ───────────────────────────────────────────

export async function triggerExport(
  projectId: string,
  runId: string,
  data: ExportRequest
): Promise<ExportRecord> {
  return apiFetch<ExportRecord>(
    `/api/v1/projects/${projectId}/runs/${runId}/export`,
    {
      method: 'POST',
      body: JSON.stringify(data),
    }
  );
}

export async function listExports(
  projectId: string,
  runId: string
): Promise<ExportListResponse> {
  return apiFetch<ExportListResponse>(
    `/api/v1/projects/${projectId}/runs/${runId}/exports`
  );
}

export async function listReportVersions(
  projectId: string,
  runId: string
): Promise<ReportVersionListResponse> {
  return apiFetch<ReportVersionListResponse>(
    `/api/v1/projects/${projectId}/runs/${runId}/reports`
  );
}


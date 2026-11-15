export type RunStatus = 'pending' | 'running' | 'completed' | 'failed' | 'awaiting_approval';

export interface ResearchRun {
  id: string;
  project_id: string;
  research_question: string;
  use_web: boolean;
  use_documents: boolean;
  workflow_mode: 'sequential' | 'multi_agent';
  // Phase 4 M4.4
  verification_depth: 'basic' | 'thorough';
  // Phase 4 M4.7 — LLM usage tracking
  llm_call_count: number;
  total_tokens_used: number;
  estimated_cost_usd: number;
  status: RunStatus;
  current_stage: string | null;
  error_message: string | null;
  started_at: string | null;
  completed_at: string | null;
  created_at: string;
}

export interface RunListResponse {
  items: ResearchRun[];
  total: number;
  limit: number;
  offset: number;
}

export interface EvidenceReference {
  source_label: string;
  source_type: 'web' | 'document';
  url?: string;
  title?: string;
  excerpt?: string;
  filename?: string;
  chunk_index?: number;
  page_number?: number;
}

export interface ReportSource {
  type: 'web' | 'document';
  url?: string;
  title?: string;
  retrieved_at?: string;
  filename?: string;
  mime_type?: string;
}

export interface ResearchReport {
  id: string;
  run_id: string;
  research_question: string;
  executive_summary: string;
  key_findings: string[];
  evidence_used: EvidenceReference[];
  observations: string | null;
  contradictions: string | null;
  limitations: string;
  sources: ReportSource[];
  generated_at: string;
}

export interface UploadedDocument {
  id: string;
  original_filename: string;
  file_size_bytes: number;
  mime_type: string;
  uploaded_at: string;
}

export interface DocumentUploadResponse {
  uploaded: UploadedDocument[];
  rejected: Array<{ filename: string; reason: string }>;
}

export interface StartRunInput {
  research_question: string;
  use_web: boolean;
  use_documents: boolean;
  document_ids: string[];
  workflow_mode?: 'sequential' | 'multi_agent';
  // Phase 4 M4.4
  verification_depth?: 'basic' | 'thorough';
}

// ── Phase 3 types ─────────────────────────────────────────────────────────────

export type TaskStatus = 'pending' | 'running' | 'completed' | 'partial' | 'failed' | 'fatal_error';

export interface ResearchTask {
  id: string;
  objective: string;
  search_query: string;
  expected_evidence_type: string | null;
  priority: number;
  status: TaskStatus;
  findings: string | null;
  evidence_count: number;
  unanswered_questions: string[];
  limitations: string | null;
  error_message: string | null;
  started_at: string | null;
  completed_at: string | null;
  created_at: string;
}

export interface ResearchPlan {
  id: string;
  run_id: string;
  objectives: string[];
  tasks: ResearchTask[];
  plan_version: number;
  created_at: string;
  updated_at: string;
}

export interface AgentEvent {
  id: string;
  agent_name: 'supervisor' | 'planner' | 'researcher' | 'system';
  event_type: string;
  summary: string;
  input_ref: string | null;
  output_ref: string | null;
  iteration: number;
  created_at: string;
}

export interface AgentActivity {
  run_id: string;
  events: AgentEvent[];
  total: number;
}

export interface TaskListResponse {
  items: ResearchTask[];
  total: number;
}

// ── Phase 4 types ─────────────────────────────────────────────────────────────

export type VerificationStatus =
  | 'supported'
  | 'partially_supported'
  | 'contradicted'
  | 'insufficient_evidence'
  | 'unverified'
  | 'not_applicable';

export interface Source {
  id: string;
  run_id: string;
  source_type: string;
  title: string | null;
  url: string | null;
  doi: string | null;
  authors: string | null;
  publisher: string | null;
  venue: string | null;
  publication_date: string | null;
  is_peer_reviewed: boolean;
  retrieval_provider: string;
  is_accessible: boolean;
  credibility_notes: string | null;
  retrieved_at: string;
  created_at: string;
}

export interface SourceListResponse {
  run_id: string;
  items: Source[];
  total: number;
}

export interface EvidenceItem {
  id: string;
  run_id: string;
  source_type: string;
  source_label: string;
  content: string | null;
  relevance_score: number;
  fetch_status: string;
  url: string | null;
  page_title: string | null;
  retrieved_at: string | null;
  document_id: string | null;
  chunk_index: number | null;
  page_number: number | null;
  // Phase 4 M4.3
  evidence_type: string;
  evidence_relationship: string;
  section_name: string | null;
  extraction_method: string | null;
  extraction_confidence: number | null;
  source_id: string | null;
}

export interface EvidenceListResponse {
  run_id: string;
  items: EvidenceItem[];
  total: number;
}

export interface ClaimVerificationData {
  id: string;
  claim_id: string;
  run_id: string;
  verification_status: VerificationStatus;
  supporting_evidence_ids: string[];
  contradicting_evidence_ids: string[];
  reasoning_summary: string | null;
  evidence_limitations: string | null;
  confidence: number;
  verified_at: string;
}

export interface Claim {
  id: string;
  run_id: string;
  report_id: string | null;
  claim_text: string;
  claim_type: string;
  originating_section: string;
  is_high_impact: boolean;
  created_at: string;
  verification: ClaimVerificationData | null;
}

export interface ClaimListResponse {
  run_id: string;
  items: Claim[];
  total: number;
}

export interface CriticReview {
  id: string;
  run_id: string;
  review_version: number;
  overall_assessment: 'strong' | 'adequate' | 'weak' | 'inadequate';
  review_status: 'approved' | 'needs_attention' | 'rejected' | 'failed';
  recommended_action: string;
  unsupported_claims: string[];
  citation_issues: string[];
  contradictory_findings: string[];
  missing_evidence: string[];
  source_quality_issues: string[];
  reasoning_issues: string[];
  review_summary: string | null;
  created_at: string;
}

export interface Citation {
  id: string;
  run_id: string;
  report_id: string;
  claim_id: string | null;
  evidence_id: string;
  source_id: string | null;
  citation_key: string;
  page_reference: string | null;
  section_reference: string | null;
  url: string | null;
  doi: string | null;
  apa_formatted: string | null;
  ieee_formatted: string | null;
  is_verified: boolean;
  validation_notes: string | null;
  created_at: string;
}

export interface BibliographyResponse {
  run_id: string;
  report_id: string | null;
  total: number;
  verified_count: number;
  citations: Citation[];
}

// ── Phase 5 M5.5 — Approval types ─────────────────────────────────────────────

export interface ApprovalRequest {
  id: string;
  run_id: string;
  checkpoint_name: string;
  node_name: string;
  context_snapshot: Record<string, unknown>;
  status: 'pending' | 'approved' | 'rejected' | 'revision_requested' | 'expired';
  decision: string | null;
  decision_notes: string | null;
  created_at: string;
  decided_at: string | null;
  expires_at: string;
}

export interface ApprovalListResponse {
  items: ApprovalRequest[];
  total: number;
}

export interface DecisionInput {
  decision: 'approved' | 'rejected' | 'revision_requested';
  notes?: string;
}

export interface DecisionResponse {
  approval_id: string;
  decision: string;
  run_status: string;
}

// ── Phase 5 M5.6 — Export types ───────────────────────────────────────────────

export interface ExportRecord {
  id: string;
  run_id: string;
  report_id: string;
  format: 'pdf' | 'docx' | 'markdown';
  status: 'pending' | 'generating' | 'ready' | 'failed';
  file_size_bytes: number | null;
  error_message: string | null;
  created_at: string;
  completed_at: string | null;
  download_url: string | null;
}

export interface ExportListResponse {
  items: ExportRecord[];
  total: number;
}

export interface ExportRequest {
  format: 'pdf' | 'docx' | 'markdown';
  report_id?: string;
}

export interface ReportVersionItem {
  id: string;
  run_id: string;
  version_number: number;
  is_current: boolean;
  research_question: string;
  executive_summary: string;
  key_findings: string;
  observations: string | null;
  contradictions: string | null;
  limitations: string;
  sources: string;
  has_validated_citations: boolean;
  review_status: string | null;
  generated_at: string;
}

export interface ReportVersionListResponse {
  items: ReportVersionItem[];
  total: number;
}


export interface AgentTokenUsage {
  agent: string;
  label: string;
  tokens: number;
  percentage: number;
  calls: number;
  color: string;
  textColor: string;
  bgColor: string;
  borderColor: string;
  icon: string;
  description: string;
}

export interface ModelTokenUsage {
  model: string;
  tier: string;
  provider: string;
  tokens: number;
  percentage: number;
  color: string;
  status: string;
}

export interface TimelinePoint {
  date: string;
  tokens: number;
  calls: number;
  runs: number;
  cumulative: number;
}

export interface TopRunToken {
  run_id: string;
  project_id: string;
  project_title: string;
  project_category: string;
  research_question: string;
  status: string;
  tokens: number;
  percentage: number;
  calls: number;
  created_at: string;
}

export interface PictographBlock {
  id: number;
  agent: string;
  label: string;
  color: string;
  tokens: number;
}

export interface PictographData {
  quantum_size: number;
  total_blocks: number;
  blocks: PictographBlock[];
  unit_label: string;
}

export interface ResearchEquivalents {
  pages_read: number;
  books_synthesized: number;
  reading_hours_saved: number;
  commercial_api_cost: number;
  savings_usd: number;
}

export interface TokenSummaryResponse {
  total_tokens: number;
  prompt_tokens: number;
  completion_tokens: number;
  prompt_ratio: number;
  completion_ratio: number;
  total_llm_calls: number;
  estimated_cost_usd: number;
  total_runs: number;
  completed_runs: number;
  avg_tokens_per_run: number;
  efficiency_score: number;
  by_agent: AgentTokenUsage[];
  by_model: ModelTokenUsage[];
  timeline: TimelinePoint[];
  top_runs: TopRunToken[];
  pictograph: PictographData;
  equivalents: ResearchEquivalents;
  retrieved_at: string;
}

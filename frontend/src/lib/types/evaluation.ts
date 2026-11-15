export interface AccuracyMetrics {
  accuracy: number;
  precision: number;
  recall: number;
  f1_score: number;
  exact_match: number;
  semantic_similarity: number;
  rouge_1: number;
  rouge_2: number;
  rouge_l: number;
  bleu_1: number;
  bleu_2: number;
  bleu_3: number;
  bleu_4: number;
}

export interface RAGMetrics {
  context_precision: number;
  context_recall: number;
  faithfulness: number;
  answer_relevancy: number;
  context_relevancy: number;
  groundedness: number;
}

export interface AgenticMetrics {
  task_completion_rate: number;
  goal_achievement: number;
  tool_call_accuracy: number;
  tool_execution_success_rate: number;
  planning_accuracy: number;
  reasoning_quality: number;
  agent_coordination: number;
  handoff_accuracy: number;
  loop_detection_score: number;
}

export interface SafetyMetrics {
  hallucination_rate: number;
  toxicity_score: number;
  bias_score: number;
  prompt_injection_resistance: number;
  pii_leakage_rate: number;
  policy_violation_rate: number;
  guardrail_intervention_rate: number;
}

export interface PerformanceMetrics {
  response_latency_mean: number;
  response_latency_p50: number;
  response_latency_p95: number;
  response_latency_p99: number;
  time_to_first_token_seconds: number;
  tokens_per_second: number;
  input_tokens_total: number;
  output_tokens_total: number;
  cost_per_request_usd: number;
  cost_per_successful_task_usd: number;
  throughput_requests_per_minute: number;
  error_rate: number;
}

export interface AgentScorecard {
  agent_name: string;
  role_description: string;
  accuracy_score: number;
  tasks_processed: number;
  success_rate: number;
  avg_latency_seconds: number;
  token_usage: number;
  cost_usd: number;
  key_strengths: string[];
  areas_for_improvement: string[];
}

export interface MultiAgentSystemMetrics {
  total_execution_time_seconds: number;
  total_swarm_cost_usd: number;
  end_to_end_completion_rate: number;
  supervisor_agent_accuracy: number;
  conflict_resolution_rate: number;
  inter_agent_consistency: number;
  task_distribution_efficiency: number;
  communication_success_rate: number;
  agents: Record<string, AgentScorecard>;
}

export interface EvaluationDashboardResponse {
  status: string;
  eval_engine_version: string;
  system_name: string;
  composite_score: number;
  accuracy_and_quality: AccuracyMetrics;
  rag_metrics: RAGMetrics;
  agentic_metrics: AgenticMetrics;
  safety_metrics: SafetyMetrics;
  performance_metrics: PerformanceMetrics;
  multi_agent_system: MultiAgentSystemMetrics;
}

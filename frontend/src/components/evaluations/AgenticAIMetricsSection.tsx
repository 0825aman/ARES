'use client';

import { Bot, CheckCircle, Cpu, Network, Repeat, Wrench, GitFork, Compass } from 'lucide-react';
import type { AgenticMetrics } from '@/lib/types/evaluation';

interface AgenticAIMetricsSectionProps {
  metrics: AgenticMetrics;
}

export function AgenticAIMetricsSection({ metrics }: AgenticAIMetricsSectionProps) {
  const agenticItems = [
    {
      title: 'Task Completion Rate',
      value: (metrics.task_completion_rate * 100).toFixed(1),
      icon: CheckCircle,
      desc: 'Proportion of scheduled research subtasks marked completed successfully by agents.',
      highlight: 'OPTIMAL',
    },
    {
      title: 'Goal Achievement',
      value: (metrics.goal_achievement * 100).toFixed(1),
      icon: Compass,
      desc: 'Evaluates whether the autonomous multi-agent swarm achieved the high-level user research goal.',
      highlight: 'ACHIEVED',
    },
    {
      title: 'Tool Call Accuracy',
      value: (metrics.tool_call_accuracy * 100).toFixed(1),
      icon: Wrench,
      desc: 'Evaluates whether appropriate, authorized tools were selected based on the current agent role.',
      highlight: 'RBAC VERIFIED',
    },
    {
      title: 'Tool Execution Success',
      value: (metrics.tool_execution_success_rate * 100).toFixed(1),
      icon: Cpu,
      desc: 'Percentage of external API and document fetch operations completing without errors or exceptions.',
      highlight: 'STABLE',
    },
    {
      title: 'Planning Accuracy',
      value: (metrics.planning_accuracy * 100).toFixed(1),
      icon: GitFork,
      desc: 'Quality, structure, priority assignment, and logical granularity of the Planner decomposition.',
      highlight: 'HIERARCHICAL',
    },
    {
      title: 'Reasoning Quality',
      value: (metrics.reasoning_quality * 100).toFixed(1),
      icon: Bot,
      desc: 'Logical consistency between retrieved evidence, extracted claims, and synthesis observations.',
      highlight: 'CONSISTENT',
    },
    {
      title: 'Agent Coordination',
      value: (metrics.agent_coordination * 100).toFixed(1),
      icon: Network,
      desc: 'Measures active participation and balanced task distribution between the 4 swarm agents.',
      highlight: 'COLLABORATIVE',
    },
    {
      title: 'Handoff Accuracy',
      value: (metrics.handoff_accuracy * 100).toFixed(1),
      icon: GitFork,
      desc: 'Accuracy of context and payload transmissions between Planner, Researcher, Supervisor, and Critic.',
      highlight: 'ZERO LOSS',
    },
    {
      title: 'Loop Detection Score',
      value: (metrics.loop_detection_score * 100).toFixed(1),
      icon: Repeat,
      desc: 'Proximity to 100% indicates zero circular ping-pong loops or runaway supervisor iterations.',
      highlight: 'NO LOOPS',
    },
  ];

  return (
    <div className="space-y-4">
      <div>
        <h3 className="text-base font-bold text-white flex items-center gap-2">
          <Bot className="h-5 w-5 text-cyan-400" />
          3. Agentic AI Evaluation Metrics (Autonomous Swarm Execution)
        </h3>
        <p className="text-xs text-slate-400">
          Measures autonomous planning, tool invocation accuracy, handoff fidelity, and loop prevention across multi-agent workflows
        </p>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3.5">
        {agenticItems.map((item, idx) => {
          const Icon = item.icon;
          return (
            <div
              key={idx}
              className="p-4 rounded-xl bg-slate-900/90 border border-slate-800 hover:border-cyan-500/30 transition-all"
            >
              <div className="flex items-center justify-between mb-2">
                <div className="flex items-center gap-2">
                  <Icon className="h-4 w-4 text-cyan-400" />
                  <span className="text-xs font-bold font-mono text-slate-200">{item.title}</span>
                </div>
                <span className="text-[9px] font-mono px-1.5 py-0.5 rounded bg-cyan-500/10 text-cyan-400 border border-cyan-500/20">
                  {item.highlight}
                </span>
              </div>
              <div className="flex items-baseline gap-1 my-2">
                <span className="text-2xl font-bold font-mono text-white tracking-tight">{item.value}</span>
                <span className="text-xs text-slate-500 font-mono">%</span>
              </div>
              <p className="text-[11px] text-slate-400 leading-relaxed">{item.desc}</p>
            </div>
          );
        })}
      </div>
    </div>
  );
}

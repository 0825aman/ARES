'use client';

import { useState } from 'react';
import {
  Cpu,
  Database,
  ShieldCheck,
  Network,
  Activity,
  CheckCircle2,
  RefreshCw,
  Terminal,
  Zap,
  Lock,
  FileCode2,
} from 'lucide-react';
import { PageHeader } from '@/components/layout/PageHeader';
import { Button } from '@/components/ui/button';

export default function SettingsPage() {
  const [activeTab, setActiveTab] = useState<'llm' | 'database' | 'security' | 'swarm'>('llm');
  const [pingStatus, setPingStatus] = useState<{
    testing: boolean;
    success?: boolean;
    latencyMs?: number;
    message?: string;
  }>({ testing: false });

  const runLivePingTest = async () => {
    setPingStatus({ testing: true });
    const startTime = performance.now();
    try {
      const res = await fetch('/api/v1/health', { method: 'GET' });
      const latency = Math.round(performance.now() - startTime);
      if (res.ok) {
        const data = await res.json();
        setPingStatus({
          testing: false,
          success: true,
          latencyMs: latency,
          message: `Backend healthy (status: ${data.status ?? 'ok'}, latency: ${latency}ms)`,
        });
      } else {
        setPingStatus({
          testing: false,
          success: false,
          latencyMs: latency,
          message: `HTTP ${res.status}: Backend returned unexpected response`,
        });
      }
    } catch (err: unknown) {
      const latency = Math.round(performance.now() - startTime);
      setPingStatus({
        testing: false,
        success: false,
        latencyMs: latency,
        message: err instanceof Error ? err.message : 'Connection failed',
      });
    }
  };

  return (
    <div className="flex flex-col h-full overflow-hidden">
      <PageHeader
        title="System Architecture & Telemetry"
        description="Live telemetry, multi-tier LLM mesh, storage configuration, and security posture"
      >
        <Button
          onClick={runLivePingTest}
          disabled={pingStatus.testing}
          size="sm"
          className="font-mono text-xs font-bold bg-blue-600 hover:bg-blue-500 text-white border border-blue-400/40 flex items-center gap-2 shadow-lg shadow-blue-500/20"
        >
          <RefreshCw className={`h-3.5 w-3.5 ${pingStatus.testing ? 'animate-spin' : ''}`} />
          <span>{pingStatus.testing ? 'PROBING...' : 'TEST HEALTH & PING'}</span>
        </Button>
      </PageHeader>

      <div className="page-content">
        <div className="max-w-5xl space-y-6">
          {/* Top Live Status Banner if Ping Tested */}
          {pingStatus.message && (
            <div
              className={`rounded-lg border px-4 py-3 font-mono text-xs flex items-center justify-between ${
                pingStatus.success
                  ? 'border-emerald-500/40 bg-emerald-500/15 text-emerald-200'
                  : 'border-red-500/40 bg-red-500/15 text-red-200'
              }`}
            >
              <div className="flex items-center gap-2">
                {pingStatus.success ? (
                  <CheckCircle2 className="h-4 w-4 text-emerald-400 shrink-0" />
                ) : (
                  <Activity className="h-4 w-4 text-red-400 shrink-0" />
                )}
                <span className="font-semibold">{pingStatus.message}</span>
              </div>
              {pingStatus.latencyMs !== undefined && (
                <span className="font-bold text-white">{pingStatus.latencyMs} ms RTT</span>
              )}
            </div>
          )}

          {/* Navigation Tabs */}
          <div className="flex items-center gap-2 border-b border-slate-800 pb-2">
            <button
              onClick={() => setActiveTab('llm')}
              className={`flex items-center gap-2 px-4 py-2 rounded-lg font-mono text-xs font-bold transition-colors ${
                activeTab === 'llm'
                  ? 'bg-blue-600/30 text-blue-300 border border-blue-500/40'
                  : 'text-slate-300 hover:text-white hover:bg-slate-800/60'
              }`}
            >
              <Cpu className="h-4 w-4" />
              <span>LLM Fallback Mesh</span>
            </button>
            <button
              onClick={() => setActiveTab('database')}
              className={`flex items-center gap-2 px-4 py-2 rounded-lg font-mono text-xs font-bold transition-colors ${
                activeTab === 'database'
                  ? 'bg-blue-600/30 text-blue-300 border border-blue-500/40'
                  : 'text-slate-300 hover:text-white hover:bg-slate-800/60'
              }`}
            >
              <Database className="h-4 w-4" />
              <span>Storage & WAL</span>
            </button>
            <button
              onClick={() => setActiveTab('security')}
              className={`flex items-center gap-2 px-4 py-2 rounded-lg font-mono text-xs font-bold transition-colors ${
                activeTab === 'security'
                  ? 'bg-blue-600/30 text-blue-300 border border-blue-500/40'
                  : 'text-slate-300 hover:text-white hover:bg-slate-800/60'
              }`}
            >
              <ShieldCheck className="h-4 w-4" />
              <span>Security & Guardrails</span>
            </button>
            <button
              onClick={() => setActiveTab('swarm')}
              className={`flex items-center gap-2 px-4 py-2 rounded-lg font-mono text-xs font-bold transition-colors ${
                activeTab === 'swarm'
                  ? 'bg-blue-600/30 text-blue-300 border border-blue-500/40'
                  : 'text-slate-300 hover:text-white hover:bg-slate-800/60'
              }`}
            >
              <Network className="h-4 w-4" />
              <span>Agent Swarm Topology</span>
            </button>
          </div>

          {/* TAB 1: LLM FALLBACK MESH */}
          {activeTab === 'llm' && (
            <div className="space-y-4">
              <div className="tech-panel p-6 space-y-5">
                <div className="flex items-center justify-between border-b border-slate-800 pb-4">
                  <div>
                    <h3 className="font-mono text-sm font-bold text-white flex items-center gap-2">
                      <Zap className="h-4 w-4 text-amber-400" />
                      Sequential Multi-Provider Failover Pipeline
                    </h3>
                    <p className="text-xs text-slate-200 mt-1.5 leading-relaxed font-normal">
                      Zero-downtime inference architecture. When Gemini encounters rate limits or quota boundaries, requests instantly cascade down the failover chain.
                    </p>
                  </div>
                  <span className="telemetry-chip-active font-mono text-xs font-bold">4 / 4 CONFIGURED</span>
                </div>

                {/* The 4-Tier Grid */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4 pt-1">
                  {/* Tier 1: Gemini */}
                  <div className="rounded-lg border border-blue-500/50 bg-blue-950/40 p-4 space-y-2 relative overflow-hidden">
                    <div className="absolute top-2.5 right-2.5 flex items-center gap-1.5 font-mono text-[10px] text-blue-300 border border-blue-500/40 bg-blue-500/20 px-2 py-0.5 rounded font-bold">
                      <span className="h-1.5 w-1.5 rounded-full bg-blue-400 animate-pulse" />
                      PRIMARY ENGINE
                    </div>
                    <span className="font-mono text-[11px] font-bold text-blue-300 uppercase tracking-widest">
                      TIER 1 (GOOGLE DEEPMIND)
                    </span>
                    <h4 className="font-mono text-base font-bold text-white">gemini-3.1-flash-lite</h4>
                    <p className="text-xs text-slate-200 leading-relaxed">
                      Primary high-throughput research agent engine with 1,000,000 token context window and sub-second time-to-first-token.
                    </p>
                    <div className="pt-2 flex items-center gap-2 font-mono text-xs text-slate-200">
                      <span className="text-emerald-400 font-bold">Active:</span> 15 RPM / 1M TPM / Zero Token Exhaustion
                    </div>
                  </div>

                  {/* Tier 2: Groq */}
                  <div className="rounded-lg border border-slate-700 bg-slate-950/80 p-4 space-y-2 relative">
                    <div className="absolute top-2.5 right-2.5 flex items-center gap-1.5 font-mono text-[10px] text-emerald-300 border border-emerald-500/40 bg-emerald-500/20 px-2 py-0.5 rounded font-bold">
                      READY / STANDBY
                    </div>
                    <span className="font-mono text-[11px] font-bold text-cyan-300 uppercase tracking-widest">
                      TIER 2 (GROQ LPU)
                    </span>
                    <h4 className="font-mono text-base font-bold text-white">qwen/qwen3.8-27b</h4>
                    <p className="text-xs text-slate-200 leading-relaxed">
                      Ultra-low latency hardware acceleration via Groq LPUs. Engaged automatically on primary 429/503 rate-limit events.
                    </p>
                    <div className="pt-2 flex items-center gap-2 font-mono text-xs text-slate-200">
                      <span className="text-cyan-400 font-bold">Speed:</span> ~500 tokens/sec stream rate
                    </div>
                  </div>

                  {/* Tier 3: OpenRouter */}
                  <div className="rounded-lg border border-slate-700 bg-slate-950/80 p-4 space-y-2 relative">
                    <div className="absolute top-2.5 right-2.5 flex items-center gap-1.5 font-mono text-[10px] text-emerald-300 border border-emerald-500/40 bg-emerald-500/20 px-2 py-0.5 rounded font-bold">
                      READY / STANDBY
                    </div>
                    <span className="font-mono text-[11px] font-bold text-purple-300 uppercase tracking-widest">
                      TIER 3 (OPENROUTER MESH)
                    </span>
                    <h4 className="font-mono text-base font-bold text-white">meta-llama/llama-3.1-8b-instruct</h4>
                    <p className="text-xs text-slate-200 leading-relaxed">
                      Decentralized high-availability API routing mesh across tier-1 data centers.
                    </p>
                    <div className="pt-2 flex items-center gap-2 font-mono text-xs text-slate-200">
                      <span className="text-purple-300 font-bold">Redundancy:</span> Global multi-datacenter pool
                    </div>
                  </div>

                  {/* Tier 4: IBM watsonx */}
                  <div className="rounded-lg border border-slate-700 bg-slate-950/80 p-4 space-y-2 relative">
                    <div className="absolute top-2.5 right-2.5 flex items-center gap-1.5 font-mono text-[10px] text-amber-300 border border-amber-500/40 bg-amber-500/20 px-2 py-0.5 rounded font-bold">
                      TOKEN GUARDED
                    </div>
                    <span className="font-mono text-[11px] font-bold text-indigo-300 uppercase tracking-widest">
                      TIER 4 (IBM WATSONX.AI)
                    </span>
                    <h4 className="font-mono text-base font-bold text-white">meta-llama/llama-3-3-70b-instruct</h4>
                    <p className="text-xs text-slate-200 leading-relaxed">
                      Enterprise high-capacity 70B parameter model. Protected from token exhaustion by preceding tiers.
                    </p>
                    <div className="pt-2 flex items-center gap-2 font-mono text-xs text-slate-200">
                      <span className="text-indigo-300 font-bold">Capacity:</span> 70 Billion parameters / Deep research
                    </div>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* TAB 2: DATABASE & STORAGE */}
          {activeTab === 'database' && (
            <div className="tech-panel p-6 space-y-5">
              <div className="border-b border-slate-800 pb-4">
                <h3 className="font-mono text-sm font-bold text-white flex items-center gap-2">
                  <Database className="h-4 w-4 text-emerald-400" />
                  SQLite 3 Enterprise-Grade Storage Engine
                </h3>
                <p className="text-xs text-slate-200 mt-1.5 leading-relaxed font-normal">
                  Configured with Write-Ahead Logging (WAL) and concurrent reader isolation for production-grade durability.
                </p>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 font-mono text-xs">
                <div className="rounded-lg border border-slate-700 bg-slate-950 p-4 space-y-1.5">
                  <span className="text-xs text-slate-400 uppercase tracking-wider font-bold">Journal Mode</span>
                  <p className="text-white font-bold text-sm">PRAGMA journal_mode = WAL</p>
                  <p className="text-xs text-slate-300 leading-relaxed">Readers do not block writers; writers do not block readers.</p>
                </div>

                <div className="rounded-lg border border-slate-700 bg-slate-950 p-4 space-y-1.5">
                  <span className="text-xs text-slate-400 uppercase tracking-wider font-bold">Lock Contention</span>
                  <p className="text-white font-bold text-sm">PRAGMA busy_timeout = 5000</p>
                  <p className="text-xs text-slate-300 leading-relaxed">5-second exponential backoff avoids SQLITE_BUSY under heavy write traffic.</p>
                </div>

                <div className="rounded-lg border border-slate-700 bg-slate-950 p-4 space-y-1.5">
                  <span className="text-xs text-slate-400 uppercase tracking-wider font-bold">Referential Integrity</span>
                  <p className="text-white font-bold text-sm">PRAGMA foreign_keys = ON</p>
                  <p className="text-xs text-slate-300 leading-relaxed">Cascading deletes and relational constraints strictly enforced.</p>
                </div>

                <div className="rounded-lg border border-slate-700 bg-slate-950 p-4 space-y-1.5">
                  <span className="text-xs text-slate-400 uppercase tracking-wider font-bold">Async Driver</span>
                  <p className="text-white font-bold text-sm">aiosqlite + SQLAlchemy 2.0</p>
                  <p className="text-xs text-slate-300 leading-relaxed">Non-blocking threadpool IO executor for all FastAPI routes.</p>
                </div>
              </div>
            </div>
          )}

          {/* TAB 3: SECURITY & GUARDRAILS */}
          {activeTab === 'security' && (
            <div className="tech-panel p-6 space-y-5">
              <div className="border-b border-slate-800 pb-4">
                <h3 className="font-mono text-sm font-bold text-white flex items-center gap-2">
                  <ShieldCheck className="h-4 w-4 text-blue-400" />
                  Multi-Layer Defensive Security Posture
                </h3>
                <p className="text-xs text-slate-200 mt-1.5 leading-relaxed font-normal">
                  Active security barriers protecting the research pipeline from injection, exfiltration, and SSRF.
                </p>
              </div>

              <div className="space-y-4 font-mono text-xs">
                <div className="flex items-start gap-3.5 rounded-lg border border-slate-700 bg-slate-950 p-4">
                  <Lock className="h-4 w-4 text-emerald-400 shrink-0 mt-0.5" />
                  <div className="space-y-1">
                    <p className="text-white font-bold text-sm">SSRF & Cloud Metadata Filtering</p>
                    <p className="text-xs text-slate-200 leading-relaxed">
                      Outbound HTTP requests block loopback (`127.0.0.1`), link-local (`169.254.169.254`), and private RFC 1918 subnets (`10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`). All redirect chains re-validate target IPs.
                    </p>
                  </div>
                </div>

                <div className="flex items-start gap-3.5 rounded-lg border border-slate-700 bg-slate-950 p-4">
                  <FileCode2 className="h-4 w-4 text-cyan-400 shrink-0 mt-0.5" />
                  <div className="space-y-1">
                    <p className="text-white font-bold text-sm">File Upload Magic Byte Inspection</p>
                    <p className="text-xs text-slate-200 leading-relaxed">
                      Uploaded assets are inspected at the binary level. File extensions are validated against true magic bytes (`%PDF-`, `\x89PNG`, `\xFF\xD8\xFF`) to stop executable polyglot attacks.
                    </p>
                  </div>
                </div>

                <div className="flex items-start gap-3.5 rounded-lg border border-slate-700 bg-slate-950 p-4">
                  <Terminal className="h-4 w-4 text-indigo-400 shrink-0 mt-0.5" />
                  <div className="space-y-1">
                    <p className="text-white font-bold text-sm">Prompt Injection & Jailbreak Neutralization</p>
                    <p className="text-xs text-slate-200 leading-relaxed">
                      User questions, external web scrapes, and citations are isolated inside structured delimiter frames (`&lt;untrusted_content&gt;...&lt;/untrusted_content&gt;`) preventing instruction hijacking.
                    </p>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* TAB 4: SWARM TOPOLOGY */}
          {activeTab === 'swarm' && (
            <div className="tech-panel p-6 space-y-5">
              <div className="border-b border-slate-800 pb-4">
                <h3 className="font-mono text-sm font-bold text-white flex items-center gap-2">
                  <Network className="h-4 w-4 text-cyan-400" />
                  Autonomous Agent Swarm Topology
                </h3>
                <p className="text-xs text-slate-200 mt-1.5 leading-relaxed font-normal">
                  Hierarchical supervisor-critic state machine designed for verified research synthesis.
                </p>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div className="rounded-lg border border-slate-700 bg-slate-950 p-4 space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="font-mono text-xs text-cyan-300 font-bold">NODE 01</span>
                    <span className="telemetry-chip font-mono text-[10px] font-bold">DAG PLANNER</span>
                  </div>
                  <h4 className="font-mono text-sm font-bold text-white">Planner Agent</h4>
                  <p className="text-xs text-slate-200 leading-relaxed">
                    Deconstructs research questions into targeted sub-questions, generates dependency DAGs, and estimates evidence thresholds.
                  </p>
                </div>

                <div className="rounded-lg border border-slate-700 bg-slate-950 p-4 space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="font-mono text-xs text-emerald-300 font-bold">NODE 02</span>
                    <span className="telemetry-chip font-mono text-[10px] font-bold">EVIDENCE RETRIEVER</span>
                  </div>
                  <h4 className="font-mono text-sm font-bold text-white">Researcher Agent</h4>
                  <p className="text-xs text-slate-200 leading-relaxed">
                    Executes multi-provider web queries, extracts verified content snippets, validates source authority, and computes citation hashes.
                  </p>
                </div>

                <div className="rounded-lg border border-slate-700 bg-slate-950 p-4 space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="font-mono text-xs text-violet-300 font-bold">NODE 03</span>
                    <span className="telemetry-chip font-mono text-[10px] font-bold">LOOP CONTROLLER</span>
                  </div>
                  <h4 className="font-mono text-sm font-bold text-white">Supervisor Agent</h4>
                  <p className="text-xs text-slate-200 leading-relaxed">
                    Coordinates execution iterations, checks information coverage completeness, halts infinite loops, and evaluates evidence depth.
                  </p>
                </div>

                <div className="rounded-lg border border-slate-700 bg-slate-950 p-4 space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="font-mono text-xs text-amber-300 font-bold">NODE 04</span>
                    <span className="telemetry-chip font-mono text-[10px] font-bold">ADVERSARIAL VERIFIER</span>
                  </div>
                  <h4 className="font-mono text-sm font-bold text-white">Critic Agent</h4>
                  <p className="text-xs text-slate-200 leading-relaxed">
                    Conducts cross-source verification, identifies unsupported claims or logical contradictions, and returns low-confidence findings for re-investigation.
                  </p>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

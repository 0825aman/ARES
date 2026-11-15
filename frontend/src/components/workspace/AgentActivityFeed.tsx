'use client';

import { useEffect, useRef, useState, useCallback, useMemo } from 'react';
import {
  Terminal,
  Bot,
  Brain,
  Search,
  Settings2,
  ChevronDown,
  ChevronUp,
  Filter,
} from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { getActivity } from '@/lib/api/runs';
import type { AgentEvent } from '@/lib/types/run';

const MAX_EVENTS = 250;
const FALLBACK_POLL_INTERVAL = 60_000;

interface AgentActivityFeedProps {
  projectId: string;
  runId: string;
  liveEvents?: AgentEvent[];
  sseConnected?: boolean;
  runCompleted?: boolean;
}

const AGENT_CONFIG: Record<
  string,
  { label: string; icon: React.ElementType; chipClass: string }
> = {
  supervisor: {
    label: 'SUPERVISOR',
    icon: Brain,
    chipClass: 'text-violet-300 bg-violet-500/20 border-violet-500/40 font-bold',
  },
  planner: {
    label: 'PLANNER',
    icon: Settings2,
    chipClass: 'text-blue-300 bg-blue-500/20 border-blue-500/40 font-bold',
  },
  researcher: {
    label: 'RESEARCHER',
    icon: Search,
    chipClass: 'text-emerald-300 bg-emerald-500/20 border-emerald-500/40 font-bold',
  },
  critic: {
    label: 'CRITIC',
    icon: Brain,
    chipClass: 'text-amber-300 bg-amber-500/20 border-amber-500/40 font-bold',
  },
  system: {
    label: 'SYSTEM',
    icon: Bot,
    chipClass: 'text-slate-200 bg-slate-800 border-slate-700 font-bold',
  },
};

function formatPreciseTime(iso: string): string {
  try {
    const d = new Date(iso);
    return d.toLocaleTimeString([], {
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
    });
  } catch {
    return '00:00:00';
  }
}

function deduplicateEvents(events: AgentEvent[]): AgentEvent[] {
  const seen = new Set<string>();
  return events.filter((e) => {
    if (seen.has(e.id)) return false;
    seen.add(e.id);
    return true;
  });
}

export function AgentActivityFeed({
  projectId,
  runId,
  liveEvents,
  sseConnected = false,
  runCompleted = false,
}: AgentActivityFeedProps) {
  const [events, setEvents] = useState<AgentEvent[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [collapsed, setCollapsed] = useState(false);
  const [hasNewEvents, setHasNewEvents] = useState(false);
  const [selectedAgentFilter, setSelectedAgentFilter] = useState<string>('all');

  const scrollAreaRef = useRef<HTMLDivElement>(null);
  const bottomRef = useRef<HTMLDivElement>(null);
  const isAtBottomRef = useRef(true);

  // ── Initial REST load ──────────────────────────────────────────────────
  useEffect(() => {
    let cancelled = false;

    async function fetchActivity() {
      try {
        const data = await getActivity(projectId, runId, 250);
        if (!cancelled) {
          setEvents(data.events.slice(-MAX_EVENTS));
          setTotal(data.total);
          setLoading(false);
        }
      } catch {
        if (!cancelled) setLoading(false);
      }
    }

    fetchActivity();

    return () => {
      cancelled = true;
    };
  }, [projectId, runId]);

  // ── 60-second fallback polling ──────────────────────────────────────────
  useEffect(() => {
    if (sseConnected || runCompleted) return;

    let cancelled = false;
    const interval = setInterval(async () => {
      try {
        const data = await getActivity(projectId, runId, 250);
        if (!cancelled) {
          setEvents(data.events.slice(-MAX_EVENTS));
          setTotal(data.total);
        }
      } catch {
        // backend unreachable — keep trying
      }
    }, FALLBACK_POLL_INTERVAL);

    return () => {
      cancelled = true;
      clearInterval(interval);
    };
  }, [projectId, runId, sseConnected, runCompleted]);

  // ── Merge live SSE events ───────────────────────────────────────────────
  useEffect(() => {
    if (!liveEvents || liveEvents.length === 0) return;

    setEvents((prev) => {
      const merged = deduplicateEvents([...prev, ...liveEvents]);
      return merged.length > MAX_EVENTS ? merged.slice(merged.length - MAX_EVENTS) : merged;
    });
    setTotal((t) => t + liveEvents.length);

    if (!isAtBottomRef.current) {
      setHasNewEvents(true);
    }
  }, [liveEvents]);

  // ── Auto-scroll logic ───────────────────────────────────────────────────
  const handleScroll = useCallback(() => {
    const el = scrollAreaRef.current;
    if (!el) return;
    const atBottom = el.scrollHeight - el.scrollTop - el.clientHeight < 40;
    isAtBottomRef.current = atBottom;
    if (atBottom) setHasNewEvents(false);
  }, []);

  useEffect(() => {
    if (!collapsed && isAtBottomRef.current && bottomRef.current) {
      bottomRef.current.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }
  }, [events.length, collapsed]);

  function scrollToBottom() {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    isAtBottomRef.current = true;
    setHasNewEvents(false);
  }

  // Filtered events
  const filteredEvents = useMemo(() => {
    if (selectedAgentFilter === 'all') return events;
    return events.filter(
      (e) => e.agent_name.toLowerCase() === selectedAgentFilter.toLowerCase(),
    );
  }, [events, selectedAgentFilter]);

  return (
    <Card className="tech-panel border-slate-700 bg-slate-950 shadow-2xl relative overflow-hidden">
      {/* Terminal Title Bar */}
      <CardHeader className="py-3 px-4 bg-slate-900 border-b border-slate-800">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            {/* Terminal Window Dots */}
            <div className="flex items-center gap-1.5">
              <span className="h-2.5 w-2.5 rounded-full bg-red-500" />
              <span className="h-2.5 w-2.5 rounded-full bg-amber-500" />
              <span className="h-2.5 w-2.5 rounded-full bg-emerald-500" />
            </div>

            <CardTitle className="font-mono text-xs font-bold text-white flex items-center gap-2">
              <Terminal className="h-4 w-4 text-blue-400" />
              <span>EXECUTION TELEMETRY STREAM</span>
              <span className="text-xs text-blue-300 font-semibold">
                [{total} EVENTS]
              </span>
            </CardTitle>
          </div>

          <div className="flex items-center gap-2 font-mono text-xs">
            <span
              className={`flex items-center gap-1.5 px-2.5 py-0.5 rounded border font-semibold ${
                sseConnected
                  ? 'border-emerald-500/40 bg-emerald-500/20 text-emerald-300'
                  : 'border-slate-700 bg-slate-800 text-slate-200'
              }`}
            >
              <span
                className={`h-2 w-2 rounded-full ${
                  sseConnected ? 'bg-emerald-400 animate-pulse' : 'bg-slate-400'
                }`}
              />
              {sseConnected ? 'SSE LIVE' : 'REST BUFFERED'}
            </span>

            <button
              onClick={() => setCollapsed((c) => !c)}
              className="text-slate-300 hover:text-white transition-colors p-1"
            >
              <ChevronDown
                className={`h-4 w-4 transition-transform ${collapsed ? '-rotate-90' : ''}`}
              />
            </button>
          </div>
        </div>

        {/* Filter Pills */}
        {!collapsed && (
          <div className="flex items-center gap-1.5 pt-2.5 border-t border-slate-800/80 font-mono text-xs">
            <Filter className="h-3.5 w-3.5 text-slate-400 mr-1" />
            {(['all', 'planner', 'researcher', 'supervisor', 'critic'] as const).map((agentKey) => (
              <button
                key={agentKey}
                onClick={() => setSelectedAgentFilter(agentKey)}
                className={`px-2.5 py-0.5 rounded uppercase tracking-wider font-bold transition-colors ${
                  selectedAgentFilter === agentKey
                    ? 'bg-blue-600/40 text-blue-200 border border-blue-400/50 shadow-sm'
                    : 'text-slate-300 hover:text-white hover:bg-slate-800'
                }`}
              >
                {agentKey}
              </button>
            ))}
          </div>
        )}
      </CardHeader>

      {!collapsed && (
        <CardContent className="p-0 relative font-mono text-xs bg-slate-950">
          {loading && (
            <div className="p-4 space-y-2">
              {[1, 2, 3].map((i) => (
                <div
                  key={i}
                  className="h-9 rounded border border-slate-800 bg-slate-900 animate-pulse"
                />
              ))}
            </div>
          )}

          {!loading && filteredEvents.length === 0 && (
            <div className="py-12 text-center text-slate-300 font-mono text-xs">
              <p className="font-bold text-slate-200">-- WAITING FOR AGENT DISPATCH LOGS --</p>
              <p className="text-xs text-slate-400 mt-1">
                Telemetry events will stream here live as agents execute
              </p>
            </div>
          )}

          {!loading && filteredEvents.length > 0 && (
            <div
              ref={scrollAreaRef}
              onScroll={handleScroll}
              className="max-h-72 overflow-y-auto px-4 py-2 divide-y divide-slate-800/60"
            >
              {filteredEvents.map((event) => {
                const meta =
                  AGENT_CONFIG[event.agent_name.toLowerCase()] ?? AGENT_CONFIG.system;
                const Icon = meta.icon;

                return (
                  <div
                    key={event.id}
                    className="py-2.5 flex items-start gap-3 hover:bg-slate-900/60 transition-colors group"
                  >
                    {/* Timestamp */}
                    <span className="text-xs text-slate-300 tabular-nums shrink-0 pt-0.5 font-mono font-medium">
                      {formatPreciseTime(event.created_at)}
                    </span>

                    {/* Agent Pill */}
                    <span
                      className={`inline-flex items-center gap-1.5 px-2 py-0.5 rounded border text-[10px] font-bold uppercase tracking-wider shrink-0 ${meta.chipClass}`}
                    >
                      <Icon className="h-3 w-3" />
                      {meta.label}
                    </span>

                    {/* Event Summary */}
                    <div className="flex-1 min-w-0">
                      <p className="text-slate-100 leading-relaxed text-xs group-hover:text-white transition-colors font-sans">
                        {event.summary}
                      </p>
                      {event.iteration > 0 && (
                        <span className="inline-block mt-1 text-[10px] text-blue-300 font-bold uppercase tracking-wider">
                          Loop Cycle #{event.iteration}
                        </span>
                      )}
                    </div>
                  </div>
                );
              })}
              <div ref={bottomRef} />
            </div>
          )}

          {/* New activity indicator */}
          {hasNewEvents && !collapsed && (
            <button
              onClick={scrollToBottom}
              className="absolute bottom-3 left-1/2 -translate-x-1/2 flex items-center gap-1.5 rounded-full bg-blue-600 px-4 py-1.5 text-xs font-mono font-bold text-white shadow-xl shadow-blue-500/30 hover:bg-blue-500 transition-all border border-blue-400/50"
            >
              <ChevronUp className="h-3.5 w-3.5" />
              <span>NEW TELEMETRY LOGS</span>
            </button>
          )}
        </CardContent>
      )}
    </Card>
  );
}

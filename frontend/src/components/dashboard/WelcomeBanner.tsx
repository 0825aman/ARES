'use client';

import { useRef } from 'react';
import Link from 'next/link';
import {
  Cpu,
  ArrowRight,
  ShieldCheck,
  Activity,
  Terminal,
} from 'lucide-react';
import { Button } from '@/components/ui/button';

export function WelcomeBanner() {
  const videoRef = useRef<HTMLVideoElement>(null);

  return (
    <div className="relative overflow-hidden rounded-xl border border-slate-700 bg-gradient-to-br from-slate-900 via-slate-900 to-slate-950 p-4 sm:p-6 shadow-2xl backdrop-blur-xl">
      {/* Subtle background tech grid effect */}
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(#3b82f6_1px,transparent_1px)] [background-size:24px_24px] opacity-15" />
      
      {/* Top glowing ambient accent */}
      <div className="pointer-events-none absolute -top-24 right-1/4 h-48 w-96 rounded-full bg-blue-600/20 blur-3xl" />

      <div className="relative z-10 flex flex-col lg:flex-row gap-6 items-start lg:items-center justify-between">
        {/* Left Side: Brand, Telemetry, and Actions */}
        <div className="space-y-4 max-w-2xl flex-1">
          {/* Top Status & Failover Chips */}
          <div className="flex flex-wrap items-center gap-2">
            <span className="telemetry-chip-active flex items-center gap-1.5 font-mono text-[11px] font-bold">
              <span className="h-2 w-2 rounded-full bg-emerald-400 animate-pulse" />
              SWARM CORE ACTIVE
            </span>
            <span className="telemetry-chip font-mono text-[11px] text-blue-300 border-blue-500/40 bg-blue-500/20 font-semibold">
              <Cpu className="h-3.5 w-3.5 text-blue-400" />
              PRIMARY: GEMINI 3.1 FLASH-LITE
            </span>
            <span className="telemetry-chip font-mono text-[11px] text-slate-200 font-medium">
              FAILOVER: GROQ ➔ OPENROUTER ➔ WATSONX
            </span>
          </div>

          {/* Title & Official Emblem Logo (Enlarged 2x on Dashboard) */}
          <div className="flex flex-col sm:flex-row sm:items-center gap-5 pt-1">
            <div className="relative h-28 w-28 sm:h-32 sm:w-32 shrink-0 rounded-2xl overflow-hidden bg-slate-900/80 border border-blue-500/40 p-2 shadow-[0_0_35px_rgba(59,130,246,0.3)] ring-2 ring-sky-400/30 flex items-center justify-center group">
              <img
                src="/ares-logo.png"
                alt="ARES Official Logo"
                className="h-full w-full object-contain transition-transform duration-300 group-hover:scale-105"
              />
            </div>
            <div className="space-y-1.5">
              <div className="flex flex-wrap items-center gap-2">
                <h1 className="text-xl font-extrabold tracking-tight text-white sm:text-2xl font-mono">
                  ARES <span className="text-blue-400">{'//'}</span> MISSION CONTROL
                </h1>
                <span className="text-[9px] font-mono px-2 py-0.5 rounded bg-blue-500/20 text-blue-300 border border-blue-500/30 font-bold tracking-wider">
                  PRO v0.1.0
                </span>
              </div>
              <p className="text-xs font-mono text-sky-400 font-semibold tracking-wider uppercase">
                Autonomous Research &amp; Evidence System
              </p>
              <p className="text-sm text-slate-200 leading-relaxed font-normal max-w-xl">
                Advanced multi-agent intelligence engine. Coordinates Planner, Researcher,
                Supervisor, and Critic agents with grounded citation verification and automated LLM failover.
              </p>
            </div>
          </div>

          {/* Quick telemetry metrics */}
          <div className="grid grid-cols-2 sm:grid-cols-3 gap-2.5 pt-1 font-mono text-xs">
            <div className="flex items-center gap-2 rounded-md border border-slate-700 bg-slate-950 px-3 py-1.5 text-slate-100 font-medium shadow-sm">
              <ShieldCheck className="h-4 w-4 text-emerald-400 shrink-0" />
              <span>Grounded Verification</span>
            </div>
            <div className="flex items-center gap-2 rounded-md border border-slate-700 bg-slate-950 px-3 py-1.5 text-slate-100 font-medium shadow-sm">
              <Activity className="h-4 w-4 text-cyan-400 shrink-0" />
              <span>4-Agent Node Swarm</span>
            </div>
            <div className="col-span-2 sm:col-span-1 flex items-center gap-2 rounded-md border border-slate-700 bg-slate-950 px-3 py-1.5 text-slate-100 font-medium shadow-sm">
              <Terminal className="h-4 w-4 text-indigo-400 shrink-0" />
              <span>SSE Live Telemetry</span>
            </div>
          </div>

          {/* Action button cluster */}
          <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-3 pt-2">
            <Button
              asChild
              size="sm"
              className="bg-blue-600 hover:bg-blue-500 text-white font-mono text-xs font-bold shadow-lg shadow-blue-500/25 border border-blue-400/40 px-4 py-2 justify-center w-full sm:w-auto"
            >
              <Link href="/projects/new" className="flex items-center justify-center gap-2">
                <span>INITIALIZE MISSION</span>
                <ArrowRight className="h-3.5 w-3.5" />
              </Link>
            </Button>

            <Button
              asChild
              variant="outline"
              size="sm"
              className="border-slate-700 bg-slate-900/90 hover:bg-slate-800 text-slate-100 font-mono text-xs font-semibold px-4 py-2 justify-center w-full sm:w-auto"
            >
              <Link href="/settings">SYSTEM TELEMETRY</Link>
            </Button>
          </div>
        </div>

        {/* Right Side: ARES Logo Reveal Video Player */}
        <div className="w-full lg:w-72 xl:w-80 shrink-0">
          <div className="relative rounded-xl overflow-hidden border border-blue-500/40 bg-slate-950/90 shadow-[0_0_30px_rgba(59,130,246,0.2)] group transition-all duration-300 hover:border-blue-400/60">
            {/* Cyber corner accents */}
            <div className="absolute top-0 left-0 w-3 h-3 border-t-2 border-l-2 border-blue-400 z-20 pointer-events-none" />
            <div className="absolute top-0 right-0 w-3 h-3 border-t-2 border-r-2 border-blue-400 z-20 pointer-events-none" />
            <div className="absolute bottom-0 left-0 w-3 h-3 border-b-2 border-l-2 border-blue-400 z-20 pointer-events-none" />
            <div className="absolute bottom-0 right-0 w-3 h-3 border-b-2 border-r-2 border-blue-400 z-20 pointer-events-none" />

            {/* Video Player (permanently muted, continuous non-pausable ambient loop) */}
            <div className="relative aspect-video w-full bg-slate-950 overflow-hidden flex items-center justify-center select-none">
              <video
                ref={videoRef}
                src="/ares-reveal.webm"
                autoPlay
                muted
                playsInline
                loop
                preload="metadata"
                className="w-full h-full object-cover transition-transform duration-500 group-hover:scale-105 pointer-events-none"
                style={{ willChange: 'transform' }}
              />

              {/* Ambient scan line overlay */}
              <div className="pointer-events-none absolute inset-0 bg-gradient-to-b from-transparent via-blue-500/5 to-transparent opacity-40" />

              {/* Status indicator overlay */}
              <div className="absolute top-2 right-2 z-20 flex items-center gap-1.5 bg-slate-950/85 backdrop-blur-md px-2 py-0.5 rounded border border-emerald-500/30 text-[10px] font-mono text-emerald-400 pointer-events-none">
                <span className="h-1.5 w-1.5 rounded-full bg-emerald-400 animate-ping" />
                LIVE
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

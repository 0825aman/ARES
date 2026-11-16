'use client';

import { useState, useRef, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/lib/hooks/useAuth';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import {
  ArrowRight,
  ShieldCheck,
  Activity,
  Terminal,
  Loader2,
  Compass,
} from 'lucide-react';

export default function LoginPage() {
  const { startSession } = useAuth();
  const router = useRouter();
  const [isSubmitting, setIsSubmitting] = useState(false);
  const videoRef = useRef<HTMLVideoElement>(null);

  // Guarantee seamless video playback across Chrome, Safari, and Firefox
  useEffect(() => {
    if (videoRef.current) {
      videoRef.current.defaultMuted = true;
      videoRef.current.muted = true;
      videoRef.current.play().catch(() => {
        // Autoplay policy fallback: video remains ready
      });
    }
  }, []);

  async function handleStartResearch() {
    setIsSubmitting(true);
    try {
      if (startSession) {
        await startSession();
      } else {
        if (typeof document !== 'undefined') {
          document.cookie = 'ares_session=ares_guest_session; path=/; max-age=86400; SameSite=Lax';
        }
      }
      router.push('/');
    } catch {
      // In all cases, set session cookie and open dashboard
      if (typeof document !== 'undefined') {
        document.cookie = 'ares_session=ares_guest_session; path=/; max-age=86400; SameSite=Lax';
      }
      router.push('/');
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <div className="relative flex min-h-screen items-center justify-center bg-slate-950 p-4 sm:p-6 overflow-hidden">
      {/* Background cyber ambient grid */}
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(#3b82f6_1px,transparent_1px)] [background-size:24px_24px] opacity-15" />
      <div className="pointer-events-none absolute -top-40 -left-40 h-96 w-96 rounded-full bg-blue-600/15 blur-3xl" />
      <div className="pointer-events-none absolute -bottom-40 -right-40 h-96 w-96 rounded-full bg-indigo-600/15 blur-3xl" />

      <div className="relative z-10 w-full max-w-2xl space-y-6">
        {/* Top Header Branding */}
        <div className="text-center space-y-3">
          <div className="inline-flex h-20 w-20 items-center justify-center rounded-2xl border border-blue-500/40 bg-slate-900/90 shadow-[0_0_35px_rgba(59,130,246,0.35)] overflow-hidden p-2.5 ring-2 ring-sky-400/25">
            <img
              src="/ares-logo.png"
              alt="ARES Logo"
              className="h-full w-full object-contain"
            />
          </div>
          <div className="space-y-1">
            <div className="flex items-center justify-center gap-2">
              <h1 className="font-mono text-2xl sm:text-3xl font-extrabold tracking-tight text-white">
                ARES <span className="text-blue-400">{'//'}</span> MISSION CONTROL
              </h1>
              <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-blue-500/20 text-blue-300 border border-blue-500/40 font-bold tracking-wider">
                v0.1.0
              </span>
            </div>
            <p className="font-mono text-xs text-sky-400 font-semibold tracking-widest uppercase">
              Autonomous Research &amp; Evidence System
            </p>
          </div>
        </div>

        {/* Security & Welcome Panel */}
        <Card className="tech-panel border-slate-800 bg-slate-900/90 shadow-2xl relative overflow-hidden backdrop-blur-xl">
          {/* Top subtle glow line */}
          <div className="absolute top-0 left-0 right-0 h-[2px] bg-gradient-to-r from-transparent via-blue-500/80 to-transparent" />

          <CardHeader className="space-y-1 pb-4 border-b border-slate-800/80">
            <div className="flex items-center justify-between">
              <CardTitle className="font-mono text-sm font-bold text-slate-100 flex items-center gap-2">
                <Compass className="h-4 w-4 text-blue-400" />
                RESEARCH WORKSPACE
              </CardTitle>
              <span className="telemetry-chip font-mono text-[10px] text-emerald-400 border-emerald-500/30 flex items-center gap-1.5 font-bold">
                <span className="h-2 w-2 rounded-full bg-emerald-400 animate-pulse" />
                ONLINE
              </span>
            </div>
            <CardDescription className="font-mono text-xs text-slate-400">
              Welcome to ARES. Autonomous multi-agent intelligence ready for mission deployment.
            </CardDescription>
          </CardHeader>

          <CardContent className="pt-6 space-y-6">
            {/* Logo Reveal Welcome Video Container */}
            <div className="relative rounded-xl overflow-hidden border border-blue-500/40 bg-slate-950/90 shadow-[0_0_35px_rgba(59,130,246,0.25)] group transition-all duration-300 hover:border-blue-400/60">
              {/* Cyber corner accents */}
              <div className="absolute top-0 left-0 w-3.5 h-3.5 border-t-2 border-l-2 border-blue-400 z-20 pointer-events-none" />
              <div className="absolute top-0 right-0 w-3.5 h-3.5 border-t-2 border-r-2 border-blue-400 z-20 pointer-events-none" />
              <div className="absolute bottom-0 left-0 w-3.5 h-3.5 border-b-2 border-l-2 border-blue-400 z-20 pointer-events-none" />
              <div className="absolute bottom-0 right-0 w-3.5 h-3.5 border-b-2 border-r-2 border-blue-400 z-20 pointer-events-none" />

              {/* Video Player */}
              <div className="relative aspect-video w-full bg-slate-950 overflow-hidden flex items-center justify-center select-none">
                <video
                  ref={videoRef}
                  src="/ares-reveal.webm"
                  autoPlay
                  muted
                  playsInline
                  loop
                  preload="auto"
                  className="w-full h-full object-cover transition-transform duration-700 group-hover:scale-105 pointer-events-none"
                  style={{ willChange: 'transform' }}
                />

                {/* Ambient scan line overlay */}
                <div className="pointer-events-none absolute inset-0 bg-gradient-to-b from-transparent via-blue-500/5 to-transparent opacity-40" />
              </div>
            </div>

            {/* Quick feature telemetry chips */}
            <div className="grid grid-cols-3 gap-2 font-mono text-xs">
              <div className="flex items-center justify-center gap-1.5 rounded-md border border-slate-800 bg-slate-950/80 px-2.5 py-2 text-slate-300 text-center">
                <ShieldCheck className="h-3.5 w-3.5 text-emerald-400 shrink-0" />
                <span className="text-[11px]">Grounded Citations</span>
              </div>
              <div className="flex items-center justify-center gap-1.5 rounded-md border border-slate-800 bg-slate-950/80 px-2.5 py-2 text-slate-300 text-center">
                <Activity className="h-3.5 w-3.5 text-cyan-400 shrink-0" />
                <span className="text-[11px]">4-Agent Swarm</span>
              </div>
              <div className="flex items-center justify-center gap-1.5 rounded-md border border-slate-800 bg-slate-950/80 px-2.5 py-2 text-slate-300 text-center">
                <Terminal className="h-3.5 w-3.5 text-indigo-400 shrink-0" />
                <span className="text-[11px]">Live Telemetry</span>
              </div>
            </div>

            {/* Action Area: Start Research Button */}
            <div className="pt-2 space-y-3">
              <Button
                onClick={handleStartResearch}
                disabled={isSubmitting}
                className="w-full h-12 bg-gradient-to-r from-blue-600 via-blue-500 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 text-white font-mono text-sm font-bold tracking-wider border border-blue-400/50 shadow-[0_0_30px_rgba(59,130,246,0.35)] transition-all duration-300 hover:shadow-[0_0_40px_rgba(59,130,246,0.5)] flex items-center justify-center gap-2 group cursor-pointer"
              >
                {isSubmitting ? (
                  <>
                    <Loader2 className="h-4 w-4 animate-spin text-white" />
                    <span>INITIALIZING MISSION CONTROL…</span>
                  </>
                ) : (
                  <>
                    <span>START RESEARCH</span>
                    <ArrowRight className="h-4 w-4 transition-transform duration-300 group-hover:translate-x-1" />
                  </>
                )}
              </Button>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

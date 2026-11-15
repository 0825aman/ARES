'use client';

import { useState, useEffect } from 'react';
import { useRouter, usePathname } from 'next/navigation';
import {
  LayoutDashboard,
  FolderOpen,
  Plus,
  Zap,
  Settings,
  Sparkles,
  ArrowRight,
  ArrowLeft,
  X,
  CheckCircle2,
  HelpCircle,
  Compass,
} from 'lucide-react';
import { Button } from '@/components/ui/button';

export interface TourStep {
  id: string;
  title: string;
  badge: string;
  route: string;
  icon: any;
  summary: string;
  keynotes: string[];
}

const TOUR_STEPS: TourStep[] = [
  {
    id: 'mission-control',
    title: 'Mission Control Dashboard',
    badge: 'STAGE 1 // NERVE CENTER',
    route: '/',
    icon: LayoutDashboard,
    summary: 'The operational command center for autonomous research execution and telemetry.',
    keynotes: [
      'Displays active 4-Agent swarm status (Planner, Researcher, Supervisor, Critic).',
      'Provides live failover mesh health (Gemini ➔ Groq ➔ OpenRouter ➔ WatsonX).',
      'Ambient holographic logo reveal and real-time mission count metrics.',
    ],
  },
  {
    id: 'missions-ledger',
    title: 'Research Missions Ledger',
    badge: 'STAGE 2 // EVIDENCE ARCHIVE',
    route: '/projects',
    icon: FolderOpen,
    summary: 'Central repository where all previous and active investigations are indexed.',
    keynotes: [
      'Chronological catalog of all research questions, domains, and runs.',
      'Check grounding status: executing, completed, or awaiting human approval.',
      'Instant access to synthesized report drafts, citation graphs, and evidence files.',
    ],
  },
  {
    id: 'dispatch-mission',
    title: 'Initiate Research Mission',
    badge: 'STAGE 3 // SWARM DISPATCH',
    route: '/projects/new',
    icon: Plus,
    summary: 'Launch new multi-agent investigations with custom hypotheses and knowledge channels.',
    keynotes: [
      'Enter any research question or problem statement with detailed context.',
      'Choose Autonomous Multi-Agent Swarm (4 nodes with Critic validation) or Sequential mode.',
      'Configure search retrieval from PubMed, OpenAlex, ArXiv, and verified web sources.',
    ],
  },
  {
    id: 'token-tracker',
    title: 'Token Telemetry & Analytics',
    badge: 'STAGE 4 // COGNITIVE OBSERVABILITY',
    route: '/tokens',
    icon: Zap,
    summary: 'Real-time resource utilization, token consumption dynamics, and cost tracking.',
    keynotes: [
      'Isotype Pictograph Matrix: visual unit glyphs representing token quanta.',
      'Agent distribution donuts breaking down cognitive load per swarm node.',
      'Exportable JSON telemetry audits tracking prompt vs. completion ratios.',
    ],
  },
  {
    id: 'system-settings',
    title: 'System & Failover Mesh',
    badge: 'STAGE 5 // RESILIENCE CONFIG',
    route: '/settings',
    icon: Settings,
    summary: 'Configure primary models, failover routes, and backend system health.',
    keynotes: [
      'Configure Gemini 3.1 Flash-Lite as primary with automated fallback chains.',
      'Manage API keys, rate limits, and external source provider credentials.',
      'Database health monitoring, SQLite WAL status, and system reset controls.',
    ],
  },
  {
    id: 'ready-to-research',
    title: 'Ready for Autonomous Discovery',
    badge: 'SYSTEM READY // ARES PRIME',
    route: '/',
    icon: Sparkles,
    summary: 'You are now ready to orchestrate autonomous research missions on ARES.',
    keynotes: [
      'Start your first investigation anytime using the "INITIATE MISSION" button.',
      'All synthesized reports include deterministic citation links in PDF, Word, and Markdown.',
      'You can re-launch this guided tour anytime using the "Product Tour" button in the sidebar.',
    ],
  },
];

const LOCAL_STORAGE_KEY = 'ares_tour_completed_v1';

export function AresGuidedTour() {
  const router = useRouter();
  const pathname = usePathname();
  const [isOpen, setIsOpen] = useState(false);
  const [currentStepIndex, setCurrentStepIndex] = useState(0);

  // Auto-launch tour for first-time visitors once client is hydrated
  useEffect(() => {
    // Only launch on app pages, not on login page
    if (pathname === '/login') return;

    try {
      const hasSeenTour = localStorage.getItem(LOCAL_STORAGE_KEY);
      if (!hasSeenTour) {
        // Small delay so the page loads and renders first
        const timer = setTimeout(() => {
          setIsOpen(true);
        }, 800);
        return () => clearTimeout(timer);
      }
    } catch {
      // Ignore localStorage availability errors in private/sandboxed modes
    }
  }, [pathname]);

  // Listen for custom event to manually re-trigger tour from anywhere
  useEffect(() => {
    const handleStartTour = () => {
      setCurrentStepIndex(0);
      setIsOpen(true);
      router.push(TOUR_STEPS[0].route);
    };

    window.addEventListener('ares:start-tour', handleStartTour);
    return () => window.removeEventListener('ares:start-tour', handleStartTour);
  }, [router]);

  const currentStep = TOUR_STEPS[currentStepIndex];
  const isFirstStep = currentStepIndex === 0;
  const isLastStep = currentStepIndex === TOUR_STEPS.length - 1;
  const StepIcon = currentStep.icon;

  const handleNext = () => {
    if (isLastStep) {
      handleComplete();
      return;
    }
    const nextIndex = currentStepIndex + 1;
    setCurrentStepIndex(nextIndex);
    const nextStep = TOUR_STEPS[nextIndex];
    if (pathname !== nextStep.route) {
      router.push(nextStep.route);
    }
  };

  const handlePrev = () => {
    if (isFirstStep) return;
    const prevIndex = currentStepIndex - 1;
    setCurrentStepIndex(prevIndex);
    const prevStep = TOUR_STEPS[prevIndex];
    if (pathname !== prevStep.route) {
      router.push(prevStep.route);
    }
  };

  const handleSkip = () => {
    try {
      localStorage.setItem(LOCAL_STORAGE_KEY, 'true');
    } catch {
      // Ignore storage errors
    }
    setIsOpen(false);
  };

  const handleComplete = () => {
    try {
      localStorage.setItem(LOCAL_STORAGE_KEY, 'true');
    } catch {
      // Ignore storage errors
    }
    setIsOpen(false);
    if (pathname !== '/') {
      router.push('/');
    }
  };

  if (!isOpen || pathname === '/login') {
    return null;
  }

  const progressPercent = Math.round(((currentStepIndex + 1) / TOUR_STEPS.length) * 100);

  return (
    <>
      {/* Subtle backdrop overlay with high-tech ambiance */}
      <div
        className="fixed inset-0 z-40 bg-black/40 backdrop-blur-[2px] transition-opacity"
        onClick={handleSkip}
        aria-hidden="true"
      />

      {/* Floating Guided Tour Card */}
      <div
        role="dialog"
        aria-label="ARES Guided Onboarding Tour"
        className="fixed z-50 bottom-4 left-4 right-4 sm:left-auto sm:right-6 sm:bottom-6 sm:w-[480px] rounded-2xl border border-blue-500/40 bg-slate-900/95 p-5 shadow-[0_0_50px_rgba(0,0,0,0.85)] backdrop-blur-2xl ring-1 ring-sky-400/20 text-slate-100 flex flex-col gap-4 animate-in fade-in slide-in-from-bottom-5 duration-300"
      >
        {/* Top Progress Bar */}
        <div className="h-1.5 w-full bg-slate-800 rounded-full overflow-hidden">
          <div
            style={{ width: `${progressPercent}%` }}
            className="h-full bg-gradient-to-r from-sky-500 via-blue-500 to-indigo-500 transition-all duration-300"
          />
        </div>

        {/* Header Bar */}
        <div className="flex items-start justify-between gap-3">
          <div className="flex items-center gap-3">
            <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-gradient-to-tr from-sky-600 via-blue-600 to-indigo-600 text-white shadow-md shadow-sky-500/20 border border-blue-400/40">
              <StepIcon className="h-5 w-5" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="font-mono text-[10px] font-bold text-sky-400 uppercase tracking-wider bg-sky-500/10 px-2 py-0.5 rounded border border-sky-500/20">
                  {currentStep.badge}
                </span>
                <span className="text-[10px] font-mono text-slate-400">
                  Step {currentStepIndex + 1} of {TOUR_STEPS.length}
                </span>
              </div>
              <h3 className="font-mono text-base font-bold text-white mt-1">
                {currentStep.title}
              </h3>
            </div>
          </div>

          <button
            type="button"
            onClick={handleSkip}
            title="Skip Tutorial"
            className="p-1 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition-colors"
            aria-label="Skip Tutorial"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Summary Description */}
        <p className="text-xs text-slate-300 leading-relaxed font-normal bg-slate-950/60 p-3 rounded-lg border border-slate-800/80">
          {currentStep.summary}
        </p>

        {/* Keynotes Bullet Points */}
        <div className="space-y-2">
          <span className="text-[10px] font-mono font-bold uppercase tracking-wider text-slate-400 flex items-center gap-1.5">
            <CheckCircle2 className="h-3 w-3 text-emerald-400" />
            <span>Key Capabilities &amp; Features:</span>
          </span>
          <ul className="space-y-1.5 text-xs text-slate-200">
            {currentStep.keynotes.map((note, idx) => (
              <li key={idx} className="flex items-start gap-2">
                <span className="h-1.5 w-1.5 rounded-full bg-blue-400 mt-1.5 shrink-0" />
                <span className="leading-snug">{note}</span>
              </li>
            ))}
          </ul>
        </div>

        {/* Navigation Actions Footer */}
        <div className="flex items-center justify-between pt-2 border-t border-slate-800/80">
          <button
            type="button"
            onClick={handleSkip}
            className="text-[11px] font-mono text-slate-400 hover:text-slate-200 transition-colors underline-offset-4 hover:underline"
          >
            Skip Tutorial
          </button>

          <div className="flex items-center gap-2">
            {!isFirstStep && (
              <Button
                variant="outline"
                size="sm"
                onClick={handlePrev}
                className="border-slate-700 bg-slate-900 hover:bg-slate-800 text-slate-300 font-mono text-xs px-3"
              >
                <ArrowLeft className="h-3.5 w-3.5 mr-1" />
                Back
              </Button>
            )}

            <Button
              size="sm"
              onClick={handleNext}
              className="bg-blue-600 hover:bg-blue-500 text-white font-mono text-xs font-bold border border-blue-400/30 shadow-md shadow-blue-500/25 px-4"
            >
              <span>{isLastStep ? 'Get Started' : 'Next Step'}</span>
              <ArrowRight className="h-3.5 w-3.5 ml-1.5" />
            </Button>
          </div>
        </div>
      </div>
    </>
  );
}

/**
 * Helper function to programmatically trigger the ARES tour from anywhere.
 */
export function startAresTour() {
  if (typeof window !== 'undefined') {
    window.dispatchEvent(new CustomEvent('ares:start-tour'));
  }
}

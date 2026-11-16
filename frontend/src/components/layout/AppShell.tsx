'use client';

import { useState } from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { Menu, X, Plus } from 'lucide-react';
import { Sidebar } from './Sidebar';
import { AresGuidedTour } from '@/components/tutorial/AresGuidedTour';

interface AppShellProps {
  children: React.ReactNode;
}

export function AppShell({ children }: AppShellProps) {
  const pathname = usePathname();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const isLoginPage = pathname === '/login';

  if (isLoginPage) {
    return (
      <main className="min-h-screen bg-slate-950 text-slate-100 flex items-center justify-center p-4">
        {children}
      </main>
    );
  }

  return (
    <div className="flex h-screen overflow-hidden bg-slate-950 text-slate-100 flex-col md:flex-row">
      {/* Desktop Sidebar (Pinned on screens >= md) */}
      <div className="hidden md:flex h-full shrink-0">
        <Sidebar />
      </div>

      {/* Mobile Top Navigation Bar (Only on screens < md) */}
      <header className="md:hidden flex items-center justify-between px-4 py-3 bg-slate-900/95 border-b border-slate-800 backdrop-blur-md shrink-0 z-30">
        <div className="flex items-center gap-3">
          <button
            type="button"
            onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
            className="p-1.5 rounded-lg bg-slate-800 border border-slate-700 text-slate-200 hover:text-white hover:bg-slate-700 transition-colors"
            aria-label="Toggle navigation menu"
          >
            {mobileMenuOpen ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
          </button>
          
          <Link href="/" className="flex items-center gap-2" onClick={() => setMobileMenuOpen(false)}>
            <div className="relative h-7 w-7 rounded-lg overflow-hidden bg-slate-900 border border-blue-500/40 p-0.5 shrink-0 shadow-xs flex items-center justify-center">
              <img src="/ares-logo.png" alt="ARES Logo" className="h-full w-full object-contain" />
            </div>
            <span className="font-mono text-sm font-bold text-white tracking-wider">ARES</span>
            <span className="text-[9px] font-mono px-1 py-0.2 rounded bg-sky-500/20 text-sky-400 border border-sky-500/30 font-semibold leading-none">
              PRO
            </span>
          </Link>
        </div>

        <div className="flex items-center gap-2">
          <div className="flex items-center gap-1 font-mono text-[10px] text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded-full border border-emerald-500/20">
            <span className="h-1.5 w-1.5 rounded-full bg-emerald-400 animate-pulse"></span>
            <span>LIVE</span>
          </div>
          <Link
            href="/projects/new"
            onClick={() => setMobileMenuOpen(false)}
            className="p-1.5 rounded-lg bg-blue-600 hover:bg-blue-500 text-white shadow-md shadow-blue-500/20 border border-blue-400/40"
            title="Initialize Mission"
          >
            <Plus className="h-4 w-4" />
          </Link>
        </div>
      </header>

      {/* Mobile Drawer Backdrop & Slide-out Sheet (Only on screens < md) */}
      {mobileMenuOpen && (
        <div
          className="fixed inset-0 z-40 bg-black/70 backdrop-blur-sm transition-opacity md:hidden"
          onClick={() => setMobileMenuOpen(false)}
          aria-hidden="true"
        />
      )}

      {/* Mobile Off-Canvas Drawer */}
      <div
        className={`fixed inset-y-0 left-0 z-50 w-72 max-w-[85vw] bg-[#090D16] shadow-2xl transition-transform duration-300 ease-in-out md:hidden flex flex-col ${
          mobileMenuOpen ? 'translate-x-0' : '-translate-x-full'
        }`}
      >
        <Sidebar onNavigate={() => setMobileMenuOpen(false)} onClose={() => setMobileMenuOpen(false)} className="w-full border-r-0" />
      </div>

      {/* Main Content Area */}
      <div className="flex flex-col flex-1 min-w-0 overflow-hidden bg-slate-950">
        {children}
      </div>

      {/* Interactive Guided Onboarding Tour */}
      <AresGuidedTour />
    </div>
  );
}

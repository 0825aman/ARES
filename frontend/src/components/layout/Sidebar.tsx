'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import {
  Brain,
  LayoutDashboard,
  FolderOpen,
  Plus,
  Settings,
  LogOut,
  Cpu,
  Layers,
  Sparkles,
  Bot,
  Zap,
  X,
  Compass,
  Activity,
} from 'lucide-react';
import { type LucideIcon } from 'lucide-react';
import { cn } from '@/lib/utils/cn';
import { useAuth } from '@/lib/hooks/useAuth';
import { startAresTour } from '@/components/tutorial/AresGuidedTour';

interface NavItemProps {
  href: string;
  icon: LucideIcon;
  label: string;
  badge?: string;
  shortcut?: string;
  exact?: boolean;
  onClick?: () => void;
}

function NavItem({ href, icon: Icon, label, badge, shortcut, exact = false, onClick }: NavItemProps) {
  const pathname = usePathname();

  let active = false;
  if (exact) {
    active = pathname === href;
  } else if (href === '/projects') {
    active =
      (pathname === '/projects' || pathname.startsWith('/projects/')) &&
      pathname !== '/projects/new';
  } else {
    active = pathname === href;
  }

  return (
    <Link
      href={href}
      onClick={onClick}
      className={cn('sidebar-nav-item group justify-between', active && 'active')}
    >
      <div className="flex items-center gap-2.5">
        <Icon className={cn('nav-icon h-4 w-4 shrink-0')} />
        <span>{label}</span>
      </div>
      <div className="flex items-center gap-1.5">
        {badge && (
          <span className="text-[10px] font-mono px-1.5 py-0.2 rounded bg-sky-500/20 text-sky-300 border border-sky-500/30">
            {badge}
          </span>
        )}
        {shortcut && (
          <span className="text-[9px] font-mono text-slate-500 opacity-0 group-hover:opacity-100 transition-opacity">
            {shortcut}
          </span>
        )}
      </div>
    </Link>
  );
}

export interface SidebarProps {
  onNavigate?: () => void;
  onClose?: () => void;
  className?: string;
}

export function Sidebar({ onNavigate, onClose, className }: SidebarProps = {}) {
  const { user, logout } = useAuth();

  return (
    <aside className={cn('sidebar flex h-full w-64 flex-col shrink-0 select-none border-r border-slate-800', className)}>
      {/* Brand Header */}
      <div className="flex items-center justify-between px-5 py-4 border-b border-slate-800/80 shrink-0">
        <div className="flex items-center gap-3">
          <div className="relative flex h-10 w-10 items-center justify-center rounded-xl overflow-hidden bg-slate-900 border border-blue-500/30 shadow-md shadow-sky-500/20 ring-1 ring-sky-400/30 shrink-0 p-1">
            <img
              src="/ares-logo.png"
              alt="ARES Logo"
              className="h-full w-full object-contain"
            />
          </div>
          <div>
            <div className="flex items-center gap-1.5">
              <span className="text-sm font-bold text-white tracking-wider font-mono">ARES</span>
              <span className="text-[9px] font-mono px-1 py-0.5 rounded bg-sky-500/20 text-sky-400 border border-sky-500/30 font-semibold leading-none">
                PRO
              </span>
            </div>
            <p className="text-[10px] font-mono leading-none mt-1 text-slate-400">
              Autonomous Research &amp; Evidence
            </p>
          </div>
        </div>

        {onClose && (
          <button
            type="button"
            onClick={onClose}
            className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition-colors md:hidden"
            title="Close menu"
            aria-label="Close menu"
          >
            <X className="h-5 w-5" />
          </button>
        )}
      </div>

      {/* Live AI Engine Status Card */}
      <div className="mx-3 mt-3 p-3 rounded-lg bg-slate-900/90 border border-slate-800 shadow-inner">
        <div className="flex items-center justify-between mb-1.5">
          <span className="text-[10px] font-mono font-semibold text-slate-300 uppercase tracking-wider flex items-center gap-1.5">
            <span className="relative flex h-2 w-2">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
              <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
            </span>
            Gemini 3.1 Flash
          </span>
          <span className="text-[9px] font-mono text-emerald-400 font-bold bg-emerald-500/10 px-1 py-0.5 rounded border border-emerald-500/20">
            ACTIVE
          </span>
        </div>
        <div className="flex items-center gap-1 text-[9px] font-mono text-slate-400 truncate">
          <span className="text-slate-500">FAILOVER:</span>
          <span className="text-slate-300 font-medium">GROQ</span>
          <span className="text-slate-600">→</span>
          <span className="text-slate-300 font-medium">OPENROUTER</span>
        </div>
      </div>

      {/* Navigation */}
      <nav className="flex-1 px-3 py-4 space-y-1 overflow-y-auto">
        <p className="px-3 mb-2 text-[10px] font-mono font-bold uppercase tracking-widest text-slate-500">
          Workspaces
        </p>
        <NavItem href="/" icon={LayoutDashboard} label="Mission Control" shortcut="⌘1" exact onClick={onNavigate} />
        <NavItem href="/projects" icon={FolderOpen} label="Research Missions" shortcut="⌘2" onClick={onNavigate} />
        <NavItem href="/projects/new" icon={Plus} label="New Mission" badge="NEW" shortcut="⌘3" exact onClick={onNavigate} />
        <NavItem href="/tokens" icon={Zap} label="Token Tracker" badge="LIVE" shortcut="⌘4" exact onClick={onNavigate} />
        <NavItem href="/evaluations" icon={Activity} label="Agent & LLM Evals" badge="EVAL" shortcut="⌘5" exact onClick={onNavigate} />

        {/* Multi-Agent Swarm Telemetry Section */}
        <div className="pt-4 pb-1">
          <p className="px-3 mb-2 text-[10px] font-mono font-bold uppercase tracking-widest text-slate-500 flex items-center justify-between">
            <span>Agent Swarm</span>
            <span className="text-[9px] text-sky-400 font-normal">4 Nodes</span>
          </p>
          <div className="grid grid-cols-2 gap-1.5 px-1">
            <div className="flex items-center gap-1.5 px-2 py-1.5 rounded-md bg-slate-900/60 border border-slate-800 text-[10px] font-mono text-slate-300">
              <span className="h-1.5 w-1.5 rounded-full bg-cyan-400"></span>
              <span className="truncate">Planner</span>
            </div>
            <div className="flex items-center gap-1.5 px-2 py-1.5 rounded-md bg-slate-900/60 border border-slate-800 text-[10px] font-mono text-slate-300">
              <span className="h-1.5 w-1.5 rounded-full bg-emerald-400"></span>
              <span className="truncate">Researcher</span>
            </div>
            <div className="flex items-center gap-1.5 px-2 py-1.5 rounded-md bg-slate-900/60 border border-slate-800 text-[10px] font-mono text-slate-300">
              <span className="h-1.5 w-1.5 rounded-full bg-violet-400"></span>
              <span className="truncate">Supervisor</span>
            </div>
            <div className="flex items-center gap-1.5 px-2 py-1.5 rounded-md bg-slate-900/60 border border-slate-800 text-[10px] font-mono text-slate-300">
              <span className="h-1.5 w-1.5 rounded-full bg-amber-400"></span>
              <span className="truncate">Critic</span>
            </div>
          </div>
        </div>
      </nav>

      {/* Bottom Telemetry & User Controls */}
      <div className="p-3 border-t border-slate-800/80 space-y-1.5">
        <button
          type="button"
          onClick={() => {
            onNavigate?.();
            startAresTour();
          }}
          className="sidebar-nav-item w-full group justify-between hover:bg-slate-800/60"
        >
          <div className="flex items-center gap-2.5">
            <Compass className="nav-icon h-4 w-4 shrink-0 text-sky-400" />
            <span>Product Tour</span>
          </div>
          <span className="text-[9px] font-mono px-1.5 py-0.2 rounded bg-sky-500/10 text-sky-300 border border-sky-500/20 font-semibold">
            GUIDE
          </span>
        </button>

        <NavItem href="/settings" icon={Settings} label="System & Fallbacks" exact onClick={onNavigate} />

        {user && (
          <div className="pt-2 border-t border-slate-800/60 flex items-center justify-between px-2">
            <div className="flex items-center gap-2 min-w-0">
              <div className="h-6 w-6 rounded-full bg-slate-800 border border-slate-700 flex items-center justify-center text-[10px] font-mono text-sky-400 font-bold">
                {user.username.charAt(0).toUpperCase()}
              </div>
              <div className="min-w-0">
                <p className="text-xs font-medium text-slate-200 truncate">{user.username}</p>
                <p className="text-[9px] font-mono text-slate-500 uppercase">{user.role}</p>
              </div>
            </div>
            <button
              type="button"
              onClick={() => logout()}
              title="Sign out"
              className="p-1 rounded text-slate-400 hover:text-red-400 hover:bg-slate-800 transition-colors"
            >
              <LogOut className="h-3.5 w-3.5" />
            </button>
          </div>
        )}

        <div className="flex items-center justify-between px-2 pt-1 text-[9px] font-mono text-slate-500">
          <span>ARES Core v0.1.0</span>
          <span className="text-emerald-500 flex items-center gap-1">
            <span className="h-1 w-1 rounded-full bg-emerald-500"></span>
            WAL MODE
          </span>
        </div>
      </div>
    </aside>
  );
}

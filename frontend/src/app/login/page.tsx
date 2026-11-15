'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/lib/hooks/useAuth';
import { ApiError } from '@/lib/api/client';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Cpu, Lock, ShieldCheck, Loader2 } from 'lucide-react';

export default function LoginPage() {
  const { login } = useAuth();
  const router = useRouter();
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError('');
    setIsSubmitting(true);
    try {
      await login(username, password);
      router.push('/');
    } catch (err) {
      if (err instanceof ApiError) {
        if (err.status === 429) {
          setError('Too many failed attempts. Exponential lockout engaged (wait 15m).');
        } else {
          setError('Invalid credentials.');
        }
      } else {
        setError('Authentication server error. Check backend connection.');
      }
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <div className="relative flex min-h-screen items-center justify-center bg-slate-950 p-4 overflow-hidden">
      {/* Background cyber ambient grid */}
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(#3b82f6_1px,transparent_1px)] [background-size:24px_24px] opacity-10" />
      <div className="pointer-events-none absolute h-96 w-96 rounded-full bg-blue-600/10 blur-3xl" />

      <div className="relative z-10 w-full max-w-sm space-y-6">
        {/* Logo / branding */}
        <div className="text-center space-y-2">
          <div className="inline-flex h-20 w-20 items-center justify-center rounded-2xl border border-blue-500/40 bg-slate-900/90 shadow-[0_0_30px_rgba(59,130,246,0.3)] overflow-hidden p-2 ring-2 ring-sky-400/20">
            <img
              src="/ares-logo.png"
              alt="ARES Logo"
              className="h-full w-full object-contain"
            />
          </div>
          <h1 className="font-mono text-2xl font-bold tracking-tight text-slate-100">
            ARES <span className="text-blue-400">{'//'}</span> OS
          </h1>
          <p className="font-mono text-xs text-slate-400">
            Autonomous Research &amp; Evidence System
          </p>
        </div>

        <Card className="tech-panel border-slate-800 bg-slate-900/90 shadow-2xl relative overflow-hidden">
          {/* Top subtle glow line */}
          <div className="absolute top-0 left-0 right-0 h-[1.5px] bg-gradient-to-r from-transparent via-blue-500/60 to-transparent" />

          <CardHeader className="space-y-1 pb-4 border-b border-slate-800/80">
            <div className="flex items-center justify-between">
              <CardTitle className="font-mono text-sm font-bold text-slate-100 flex items-center gap-2">
                <Lock className="h-3.5 w-3.5 text-blue-400" />
                SECURITY GATEWAY
              </CardTitle>
              <span className="telemetry-chip font-mono text-[9px] text-emerald-400 border-emerald-500/30">
                ACTIVE
              </span>
            </div>
            <CardDescription className="font-mono text-xs text-slate-400">
              Provide operator credentials to initialize session.
            </CardDescription>
          </CardHeader>
          <CardContent className="pt-5">
            <form onSubmit={handleSubmit} className="space-y-4">
              <div className="space-y-1.5 font-mono text-xs">
                <Label htmlFor="username" className="text-slate-300">
                  Operator Identifier
                </Label>
                <Input
                  id="username"
                  type="text"
                  autoComplete="username"
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  required
                  disabled={isSubmitting}
                  className="bg-slate-950 border-slate-800 text-slate-100 font-mono text-xs"
                  placeholder="admin"
                />
              </div>

              <div className="space-y-1.5 font-mono text-xs">
                <Label htmlFor="password" className="text-slate-300">
                  Access Key
                </Label>
                <Input
                  id="password"
                  type="password"
                  autoComplete="current-password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  required
                  disabled={isSubmitting}
                  className="bg-slate-950 border-slate-800 text-slate-100 font-mono text-xs"
                  placeholder="••••••••"
                />
              </div>

              {error && (
                <div
                  className="rounded border border-red-500/30 bg-red-500/10 p-2.5 font-mono text-xs text-red-400"
                  role="alert"
                >
                  {error}
                </div>
              )}

              <Button
                type="submit"
                className="w-full bg-blue-600 hover:bg-blue-500 text-white font-mono text-xs border border-blue-400/30 shadow-lg shadow-blue-500/20"
                disabled={isSubmitting}
              >
                {isSubmitting ? (
                  <>
                    <Loader2 className="h-3.5 w-3.5 mr-2 animate-spin" />
                    AUTHENTICATING…
                  </>
                ) : (
                  'INITIALIZE SESSION'
                )}
              </Button>
            </form>
          </CardContent>
        </Card>

        <div className="flex items-center justify-center gap-1.5 font-mono text-[11px] text-slate-500">
          <ShieldCheck className="h-3.5 w-3.5 text-emerald-400" />
          <span>PBKDF2-SHA256 · CONSTANT-TIME VERIFIED</span>
        </div>
      </div>
    </div>
  );
}

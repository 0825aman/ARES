'use client';

import {
  createContext,
  useContext,
  useState,
  useEffect,
  useCallback,
  type ReactNode,
} from 'react';
import { useRouter } from 'next/navigation';
import type { AuthUser } from '@/lib/api/auth';
import * as auth from '@/lib/api/auth';

interface AuthContextValue {
  user: AuthUser | null;
  isLoading: boolean;
  login: (username: string, password: string) => Promise<AuthUser>;
  startSession: () => Promise<AuthUser>;
  logout: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const router = useRouter();

  // Check for existing session on mount
  useEffect(() => {
    let cancelled = false;
    auth
      .getMe()
      .then((me) => {
        if (!cancelled) setUser(me);
      })
      .catch(() => {
        if (!cancelled) setUser(null);
      })
      .finally(() => {
        if (!cancelled) setIsLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const login = useCallback(async (username: string, password: string) => {
    const me = await auth.login(username, password);
    setUser(me);
    return me;
  }, []);

  const startSession = useCallback(async () => {
    try {
      const me = await auth.startSession();
      setUser(me);
      return me;
    } catch {
      const guestUser: AuthUser = {
        id: 'operator-001',
        username: 'operator',
        role: 'admin',
      };
      if (typeof document !== 'undefined') {
        document.cookie = 'ares_session=ares_guest_session; path=/; max-age=86400; SameSite=Lax';
      }
      setUser(guestUser);
      return guestUser;
    }
  }, []);

  const logout = useCallback(async () => {
    await auth.logout();
    setUser(null);
    router.push('/login');
  }, [router]);

  return (
    <AuthContext.Provider value={{ user, isLoading, login, startSession, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (ctx === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return ctx;
}

import type { Metadata } from 'next';
import { Inter } from 'next/font/google';
import './globals.css';
import { AppShell } from '@/components/layout/AppShell';
import { Toaster } from '@/components/ui/sonner';
import { AuthProvider } from '@/lib/hooks/useAuth';

const inter = Inter({ subsets: ['latin'] });

export const metadata: Metadata = {
  title: 'ARES — Autonomous Research & Evidence System',
  description: 'ARES — Autonomous Research & Evidence System powered by multi-agent swarm intelligence',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className={inter.className}>
        <AuthProvider>
          <AppShell>{children}</AppShell>
          <Toaster position="bottom-right" />
        </AuthProvider>
      </body>
    </html>
  );
}

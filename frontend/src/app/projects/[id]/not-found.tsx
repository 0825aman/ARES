import Link from 'next/link';
import { Button } from '@/components/ui/button';
import { FileQuestion } from 'lucide-react';

export default function NotFound() {
  return (
    <div className="flex flex-col items-center justify-center py-24 px-6 text-center">
      <FileQuestion className="h-12 w-12 text-muted-foreground mb-4" />
      <h2 className="text-lg font-semibold text-foreground mb-2">Project not found</h2>
      <p className="text-sm text-muted-foreground max-w-xs mb-6">
        The research project you&apos;re looking for doesn&apos;t exist or may have been deleted.
      </p>
      <Button asChild>
        <Link href="/projects">Return to Research Projects</Link>
      </Button>
    </div>
  );
}

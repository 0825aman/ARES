import { Badge } from '@/components/ui/badge';
import { type LucideIcon } from 'lucide-react';

interface PlaceholderSectionProps {
  icon: LucideIcon;
  title: string;
  description: string;
}

export function PlaceholderSection({ icon: Icon, title, description }: PlaceholderSectionProps) {
  return (
    <div className="rounded-xl border border-dashed border-slate-300 bg-white p-5">
      <div className="flex items-start gap-3">
        <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-slate-100 shrink-0">
          <Icon className="h-4 w-4 text-slate-400" />
        </div>
        <div className="flex-1">
          <div className="flex items-center gap-2 mb-1">
            <span className="text-sm font-medium text-slate-700">{title}</span>
            <Badge variant="secondary" className="text-[10px] px-1.5 py-0 h-4 bg-slate-100 text-slate-500">
              Phase 2
            </Badge>
          </div>
          <p className="text-xs text-slate-400 leading-relaxed">{description}</p>
        </div>
      </div>
    </div>
  );
}

import { Badge } from '@/components/ui/badge';

interface CategoryBadgeProps {
  category: string | null;
  className?: string;
}

export function CategoryBadge({ category, className }: CategoryBadgeProps) {
  if (!category) return null;
  return (
    <Badge
      variant="outline"
      className={`font-mono text-[10px] font-medium tracking-wide bg-slate-900/80 text-cyan-400 border-cyan-500/30 px-2 py-0.5 uppercase ${className ?? ''}`}
    >
      {category}
    </Badge>
  );
}

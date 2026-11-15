interface PageHeaderProps {
  title: string;
  description?: string;
  children?: React.ReactNode;
}

export function PageHeader({ title, description, children }: PageHeaderProps) {
  return (
    <div className="page-header">
      <div className="min-w-0 flex-1">
        <h1 className="font-mono text-base sm:text-lg font-bold text-white tracking-tight flex items-center gap-2 sm:gap-2.5">
          <span className="h-2 w-2 sm:h-2.5 sm:w-2.5 rounded-full bg-blue-400 animate-pulse shrink-0" />
          <span className="truncate">{title}</span>
        </h1>
        {description && (
          <p className="font-mono text-xs text-slate-200 mt-1 font-medium line-clamp-2 sm:line-clamp-none">
            {description}
          </p>
        )}
      </div>
      {children && (
        <div className="flex items-center gap-2 shrink-0 flex-wrap sm:ml-4">{children}</div>
      )}
    </div>
  );
}

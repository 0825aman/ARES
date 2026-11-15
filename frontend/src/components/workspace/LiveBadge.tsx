"use client";

/**
 * LiveBadge — Phase 5 M5.7
 *
 * A small pulsing badge shown on tab headers to indicate live data is arriving.
 * Rendered as a subtle dot with an optional count. The pulse animation stops
 * when the run is no longer active.
 */

interface LiveBadgeProps {
  count?: number;
  active?: boolean;
}

export function LiveBadge({ count, active = true }: LiveBadgeProps) {
  if (count === undefined || count === 0) return null;

  return (
    <span className="ml-1.5 inline-flex items-center">
      {active && (
        <span className="relative mr-1 flex h-2 w-2">
          <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-blue-400 opacity-75" />
          <span className="relative inline-flex h-2 w-2 rounded-full bg-blue-500" />
        </span>
      )}
      <span className="inline-flex items-center rounded px-1 py-0 text-xs font-medium bg-slate-100 text-slate-600 leading-4">
        {count > 99 ? "99+" : count}
      </span>
    </span>
  );
}

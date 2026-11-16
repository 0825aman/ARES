"use client";

/**
 * ExportPanel — Phase 5 M5.6
 *
 * Displays report export controls: PDF, DOCX, and Markdown download buttons,
 * plus a list of previous exports. Rendered below ResearchReportView when a
 * completed run has a report.
 */

import { useState, useEffect } from "react";
import { Download, FileText, File, Hash, ChevronDown, ChevronUp } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";
import { triggerExport, listExports } from "@/lib/api/runs";
import { getApiBaseUrl } from "@/lib/api/client";
import type { ExportRecord } from "@/lib/types/run";

interface ExportPanelProps {
  projectId: string;
  runId: string;
  reportId?: string;
  reportVersionNumber?: number;
}

type ExportFormat = "pdf" | "docx" | "markdown";

const FORMAT_CONFIG: Record<ExportFormat, { label: string; ext: string; icon: React.ComponentType<{ className?: string }> }> = {
  pdf: { label: "PDF", ext: "pdf", icon: FileText },
  docx: { label: "Word Doc", ext: "docx", icon: File },
  markdown: { label: "Markdown", ext: "md", icon: Hash },
};

function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function timeAgo(isoDate: string): string {
  const diff = Date.now() - new Date(isoDate).getTime();
  const mins = Math.floor(diff / 60_000);
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  return `${Math.floor(hrs / 24)}d ago`;
}

export function ExportPanel({ projectId, runId, reportId, reportVersionNumber }: ExportPanelProps) {
  const [expanded, setExpanded] = useState(false);
  const [generating, setGenerating] = useState<ExportFormat | null>(null);
  const [exportError, setExportError] = useState<string | null>(null);
  const [exports, setExports] = useState<ExportRecord[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!expanded) return;
    setLoading(true);
    listExports(projectId, runId)
      .then((data) => setExports(data.items))
      .catch(() => {/* silent */})
      .finally(() => setLoading(false));
  }, [expanded, projectId, runId]);

  async function handleExport(format: ExportFormat) {
    setGenerating(format);
    setExportError(null);
    try {
      const record = await triggerExport(projectId, runId, { format, report_id: reportId });
      if (record.download_url) {
        // Trigger browser download with cache-busting timestamp and distinct filename
        const a = document.createElement("a");
        const base = getApiBaseUrl();
        const rawUrl = record.download_url.startsWith("http")
          ? record.download_url
          : `${base}${record.download_url.startsWith("/") ? "" : "/"}${record.download_url}`;
        const separator = rawUrl.includes("?") ? "&" : "?";
        a.href = `${rawUrl}${separator}t=${Date.now()}`;
        a.download = `ARES_Report_${record.id.slice(0, 8)}.${FORMAT_CONFIG[format].ext}`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
      }
      // Refresh list
      setExports((prev) => [record, ...prev]);
    } catch (err) {
      setExportError(err instanceof Error ? err.message : "Export failed.");
    } finally {
      setGenerating(null);
    }
  }

  async function handleRedownload(exp: ExportRecord) {
    if (!exp.download_url) return;
    const a = document.createElement("a");
    const base = getApiBaseUrl();
    const rawUrl = exp.download_url.startsWith("http")
      ? exp.download_url
      : `${base}${exp.download_url.startsWith("/") ? "" : "/"}${exp.download_url}`;
    const separator = rawUrl.includes("?") ? "&" : "?";
    a.href = `${rawUrl}${separator}t=${Date.now()}`;
    const ext = FORMAT_CONFIG[exp.format as ExportFormat]?.ext ?? exp.format;
    a.download = `ARES_Report_${exp.id.slice(0, 8)}.${ext}`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
  }

  return (
    <div className="mt-4 rounded-lg border border-slate-200 bg-white">
      {/* Header / toggle */}
      <button
        type="button"
        className="flex w-full items-center justify-between px-4 py-3 text-sm font-medium text-slate-700 hover:bg-slate-50 transition-colors rounded-lg"
        onClick={() => setExpanded((v) => !v)}
        aria-expanded={expanded}
      >
        <span className="flex items-center gap-2">
          <Download className="h-4 w-4 text-slate-400" />
          Export Report
          {reportVersionNumber && reportVersionNumber > 1 && (
            <span className="ml-1 text-xs text-slate-400">v{reportVersionNumber}</span>
          )}
        </span>
        {expanded ? (
          <ChevronUp className="h-4 w-4 text-slate-400" />
        ) : (
          <ChevronDown className="h-4 w-4 text-slate-400" />
        )}
      </button>

      {expanded && (
        <div className="border-t border-slate-100 px-4 py-4 space-y-4">
          {/* Format buttons */}
          <div>
            <p className="text-xs font-medium text-slate-500 mb-2">Download as</p>
            <div className="flex flex-wrap gap-2">
              {(["pdf", "docx", "markdown"] as ExportFormat[]).map((fmt) => {
                const cfg = FORMAT_CONFIG[fmt];
                const Icon = cfg.icon;
                return (
                  <Button
                    key={fmt}
                    variant="outline"
                    size="sm"
                    disabled={generating !== null}
                    onClick={() => handleExport(fmt)}
                    className="gap-1.5"
                  >
                    {generating === fmt ? (
                      <span className="inline-block h-3 w-3 animate-spin rounded-full border border-current border-t-transparent" />
                    ) : (
                      <Icon className="h-3.5 w-3.5" />
                    )}
                    {cfg.label}
                  </Button>
                );
              })}
            </div>
            {exportError && (
              <p className="mt-2 text-xs text-red-600">{exportError}</p>
            )}
          </div>

          {/* Previous exports */}
          {(loading || exports.length > 0) && (
            <>
              <Separator />
              <div>
                <p className="text-xs font-medium text-slate-500 mb-2">Previous exports</p>
                {loading ? (
                  <div className="text-xs text-slate-400">Loading…</div>
                ) : (
                  <div className="space-y-1.5">
                    {exports.map((exp) => (
                      <div
                        key={exp.id}
                        className="flex items-center justify-between gap-2 rounded-md border border-slate-100 bg-slate-50 px-3 py-2 text-xs"
                      >
                        <div className="flex items-center gap-2 min-w-0">
                          <span className="font-medium text-slate-700 uppercase">{exp.format}</span>
                          {exp.file_size_bytes != null && (
                            <span className="text-slate-400">{formatBytes(exp.file_size_bytes)}</span>
                          )}
                          <span className="text-slate-400 truncate">{timeAgo(exp.created_at)}</span>
                        </div>
                        {exp.status === "ready" && exp.download_url && (
                          <button
                            type="button"
                            onClick={() => handleRedownload(exp)}
                            className="shrink-0 text-blue-600 hover:text-blue-700"
                            title="Re-download"
                          >
                            <Download className="h-3.5 w-3.5" />
                          </button>
                        )}
                        {exp.status === "failed" && (
                          <span className="text-red-500 text-xs">Failed</span>
                        )}
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </>
          )}
        </div>
      )}
    </div>
  );
}

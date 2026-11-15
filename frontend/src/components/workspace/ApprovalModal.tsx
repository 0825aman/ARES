"use client";

/**
 * ApprovalModal — Phase 5 M5.5
 *
 * Full-screen dialog for reviewing an approval checkpoint.
 * Shows the context snapshot (research plan or critic decision) and lets the
 * user approve, request revision, or reject the run.
 */

import { useState } from "react";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import { CheckCircle2, RotateCcw, XCircle, AlertCircle } from "lucide-react";
import { submitApprovalDecision } from "@/lib/api/runs";
import type { ApprovalRequest } from "@/lib/types/run";

interface ApprovalModalProps {
  open: boolean;
  approval: ApprovalRequest | null;
  projectId: string;
  runId: string;
  onClose: () => void;
  onResolved: (decision: string) => void;
}

const CHECKPOINT_LABELS: Record<string, string> = {
  plan_approval: "Research Plan Approval",
  critic_needs_attention: "Critic Review Approval",
};

type Decision = "approved" | "rejected" | "revision_requested";

export function ApprovalModal({
  open,
  approval,
  projectId,
  runId,
  onClose,
  onResolved,
}: ApprovalModalProps) {
  const [decision, setDecision] = useState<Decision | null>(null);
  const [notes, setNotes] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);

  const label = approval
    ? (CHECKPOINT_LABELS[approval.checkpoint_name] ?? approval.checkpoint_name)
    : '';
  const snapshot = (approval?.context_snapshot ?? {}) as Record<string, unknown>;
  const researchPlan = snapshot?.research_plan as Record<string, unknown> | null | undefined;
  const criticDecision = snapshot?.critic_decision as string | null | undefined;
  const researchQuestion = snapshot?.research_question as string | null | undefined;

  if (!approval) return null;

  async function handleSubmit() {
    if (!decision || !approval) return;
    if (decision === "revision_requested" && !notes.trim()) return;

    setSubmitting(true);
    setSubmitError(null);

    try {
      await submitApprovalDecision(projectId, runId, approval.id, {
        decision,
        notes: notes.trim() || undefined,
      });
      onResolved(decision);
      onClose();
    } catch (err) {
      setSubmitError(err instanceof Error ? err.message : "Failed to submit decision.");
    } finally {
      setSubmitting(false);
    }
  }

  function handleClose() {
    if (submitting) return;
    setDecision(null);
    setNotes("");
    setSubmitError(null);
    onClose();
  }

  return (
    <Dialog open={open} onOpenChange={handleClose}>
      <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <AlertCircle className="h-5 w-5 text-amber-500" />
            {label}
          </DialogTitle>
          <DialogDescription>
            The research workflow has paused at a checkpoint. Review the information
            below and choose how to proceed.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 py-2">
          {/* Research question */}
          {researchQuestion && (
            <div>
              <p className="text-xs font-medium uppercase tracking-wide text-slate-500 mb-1">
                Research Question
              </p>
              <p className="text-sm text-slate-700">{researchQuestion}</p>
            </div>
          )}

          <Separator />

          {/* Research plan summary */}
          {researchPlan && (
            <div>
              <p className="text-xs font-medium uppercase tracking-wide text-slate-500 mb-2">
                Research Plan
              </p>
              {Array.isArray((researchPlan as Record<string, unknown>)?.tasks) ? (
                <div className="space-y-2">
                  {((researchPlan as Record<string, unknown>).tasks as unknown[]).map(
                    (task: unknown, i: number) => {
                      const t = task as Record<string, unknown>;
                      return (
                        <div
                          key={i}
                          className="rounded-md border border-slate-100 bg-slate-50 px-3 py-2 text-sm"
                        >
                          <p className="font-medium text-slate-800">
                            {i + 1}. {String(t.title ?? t.name ?? "Task")}
                          </p>
                          {t.description != null && (
                            <p className="mt-0.5 text-xs text-slate-500">
                              {String(t.description)}
                            </p>
                          )}
                        </div>
                      );
                    }
                  )}
                </div>
              ) : (
                <pre className="whitespace-pre-wrap text-xs text-slate-700 bg-slate-50 rounded p-2 max-h-48 overflow-y-auto">
                  {JSON.stringify(researchPlan, null, 2)}
                </pre>
              )}
            </div>
          )}

          {/* Critic decision */}
          {criticDecision && (
            <div>
              <p className="text-xs font-medium uppercase tracking-wide text-slate-500 mb-1">
                Critic Decision
              </p>
              <Badge
                variant="secondary"
                className={
                  criticDecision === "mark_needs_attention" ||
                  criticDecision === "needs_attention"
                    ? "bg-amber-100 text-amber-800"
                    : "bg-slate-100 text-slate-700"
                }
              >
                {criticDecision}
              </Badge>
            </div>
          )}

          <Separator />

          {/* Decision selector */}
          <div className="space-y-2">
            <p className="text-xs font-medium uppercase tracking-wide text-slate-500">
              Your Decision
            </p>
            <div className="flex flex-wrap gap-2">
              <button
                type="button"
                onClick={() => setDecision("approved")}
                className={`flex items-center gap-1.5 rounded-md border px-3 py-2 text-sm transition-colors ${
                  decision === "approved"
                    ? "border-emerald-400 bg-emerald-50 text-emerald-800 font-medium"
                    : "border-slate-200 text-slate-700 hover:border-emerald-300 hover:bg-emerald-50"
                }`}
              >
                <CheckCircle2 className="h-4 w-4" />
                Approve
              </button>
              <button
                type="button"
                onClick={() => setDecision("revision_requested")}
                className={`flex items-center gap-1.5 rounded-md border px-3 py-2 text-sm transition-colors ${
                  decision === "revision_requested"
                    ? "border-blue-400 bg-blue-50 text-blue-800 font-medium"
                    : "border-slate-200 text-slate-700 hover:border-blue-300 hover:bg-blue-50"
                }`}
              >
                <RotateCcw className="h-4 w-4" />
                Request Revision
              </button>
              <button
                type="button"
                onClick={() => setDecision("rejected")}
                className={`flex items-center gap-1.5 rounded-md border px-3 py-2 text-sm transition-colors ${
                  decision === "rejected"
                    ? "border-red-400 bg-red-50 text-red-800 font-medium"
                    : "border-slate-200 text-slate-700 hover:border-red-300 hover:bg-red-50"
                }`}
              >
                <XCircle className="h-4 w-4" />
                Reject
              </button>
            </div>
          </div>

          {/* Notes field — always shown but required only for revision */}
          <div className="space-y-1">
            <Label htmlFor="approval-notes" className="text-xs text-slate-500">
              Notes{" "}
              {decision === "revision_requested" && (
                <span className="text-red-500">*</span>
              )}
              {decision !== "revision_requested" && "(optional)"}
            </Label>
            <Textarea
              id="approval-notes"
              placeholder={
                decision === "revision_requested"
                  ? "Describe what should be revised…"
                  : "Add any notes for the record…"
              }
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              rows={3}
              className="text-sm"
            />
          </div>

          {/* Rejection warning */}
          {decision === "rejected" && (
            <div className="rounded-md border border-red-200 bg-red-50 px-3 py-2 text-xs text-red-700">
              <strong>Warning:</strong> Rejecting will permanently stop this run.
              The run will be marked as failed and cannot be resumed.
            </div>
          )}

          {/* Submit error */}
          {submitError && (
            <div className="rounded-md border border-red-200 bg-red-50 px-3 py-2 text-xs text-red-700">
              {submitError}
            </div>
          )}
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={handleClose} disabled={submitting}>
            Cancel
          </Button>
          <Button
            onClick={handleSubmit}
            disabled={
              !decision ||
              submitting ||
              (decision === "revision_requested" && !notes.trim())
            }
            className={
              decision === "rejected"
                ? "bg-red-600 hover:bg-red-700 text-white"
                : ""
            }
          >
            {submitting
              ? "Submitting…"
              : decision === "approved"
              ? "Approve & Continue"
              : decision === "revision_requested"
              ? "Submit Revision Request"
              : decision === "rejected"
              ? "Reject Run"
              : "Submit"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

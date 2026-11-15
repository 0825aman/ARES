"use client";

/**
 * ApprovalBanner — Phase 5 M5.5
 *
 * Displayed at the top of the active-run workspace when the graph suspends
 * at a human-approval checkpoint.  The banner prompts the user to review the
 * plan / critic output and shows a button to open the full ApprovalModal.
 */

import { AlertTriangle, CheckCircle, XCircle, MessageSquare } from "lucide-react";
import { Button } from "@/components/ui/button";
import type { ApprovalRequest } from "@/lib/types/run";

interface ApprovalBannerProps {
  approval: ApprovalRequest;
  onOpenModal: () => void;
}

const CHECKPOINT_LABELS: Record<string, string> = {
  plan_approval: "Research Plan",
  critic_needs_attention: "Critic Review",
};

export function ApprovalBanner({ approval, onOpenModal }: ApprovalBannerProps) {
  const label =
    CHECKPOINT_LABELS[approval.checkpoint_name] ?? approval.checkpoint_name;

  return (
    <div className="mb-4 flex items-start gap-3 rounded-lg border border-amber-200 bg-amber-50 px-4 py-3">
      <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-amber-600" />
      <div className="flex-1 min-w-0">
        <p className="text-sm font-medium text-amber-900">
          Approval Required — {label}
        </p>
        <p className="mt-0.5 text-xs text-amber-700">
          The research workflow has paused and is waiting for your review before
          continuing.
        </p>
      </div>
      <Button
        size="sm"
        variant="outline"
        className="shrink-0 border-amber-300 text-amber-800 hover:bg-amber-100"
        onClick={onOpenModal}
      >
        Review
      </Button>
    </div>
  );
}

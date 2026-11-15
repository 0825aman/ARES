'use client';

import { useState } from 'react';
import { toast } from 'sonner';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Loader2 } from 'lucide-react';
import { updateProject } from '@/lib/api/projects';
import { ApiError } from '@/lib/api/client';
import type { ProjectStatus } from '@/lib/types/project';

const STATUS_OPTIONS: { value: ProjectStatus; label: string }[] = [
  { value: 'not_started', label: 'Not Started' },
  { value: 'in_progress', label: 'In Progress' },
  { value: 'completed', label: 'Completed' },
  { value: 'archived', label: 'Archived' },
];

interface StatusSelectorProps {
  projectId: string;
  currentStatus: ProjectStatus;
}

export function StatusSelector({ projectId, currentStatus }: StatusSelectorProps) {
  const [status, setStatus] = useState<ProjectStatus>(currentStatus);
  const [isUpdating, setIsUpdating] = useState(false);

  async function handleChange(newStatus: ProjectStatus) {
    if (newStatus === status) return;
    setIsUpdating(true);
    try {
      await updateProject(projectId, { status: newStatus });
      setStatus(newStatus);
      toast.success('Status updated.');
    } catch (err) {
      const message = err instanceof ApiError ? err.message : 'Failed to update status.';
      toast.error(message);
    } finally {
      setIsUpdating(false);
    }
  }

  return (
    <div className="relative">
      {isUpdating && (
        <Loader2 className="h-3 w-3 animate-spin absolute -top-1 -right-1 text-muted-foreground" />
      )}
      <Select
        value={status}
        onValueChange={(v) => handleChange(v as ProjectStatus)}
        disabled={isUpdating}
      >
        <SelectTrigger className="w-36 h-8 text-xs">
          <SelectValue />
        </SelectTrigger>
        <SelectContent>
          {STATUS_OPTIONS.map((opt) => (
            <SelectItem key={opt.value} value={opt.value} className="text-xs">
              {opt.label}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
    </div>
  );
}

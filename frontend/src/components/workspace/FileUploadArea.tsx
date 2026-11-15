'use client';

import { useRef, useState, useCallback } from 'react';
import { Upload, X, FileText, File } from 'lucide-react';
import { Button } from '@/components/ui/button';

interface PendingFile {
  file: File;
  id: string;
  error?: string;
}

interface FileUploadAreaProps {
  onFilesChange: (files: File[]) => void;
  disabled?: boolean;
}

const ALLOWED_EXTS = ['.pdf', '.docx', '.txt'];
const MAX_SIZE_MB = 20;

function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function getFileIcon(name: string) {
  const ext = name.toLowerCase().split('.').pop();
  if (ext === 'pdf') return <FileText className="h-4 w-4 text-red-500" />;
  return <File className="h-4 w-4 text-blue-500" />;
}

export function FileUploadArea({ onFilesChange, disabled = false }: FileUploadAreaProps) {
  const [pendingFiles, setPendingFiles] = useState<PendingFile[]>([]);
  const [isDragging, setIsDragging] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  const validateFile = (file: File): string | undefined => {
    const ext = '.' + file.name.toLowerCase().split('.').pop();
    if (!ALLOWED_EXTS.includes(ext)) {
      return `Unsupported type '${ext}'. Accepted: PDF, DOCX, TXT.`;
    }
    if (file.size > MAX_SIZE_MB * 1024 * 1024) {
      return `Exceeds ${MAX_SIZE_MB} MB size limit.`;
    }
    return undefined;
  };

  const addFiles = useCallback((newFiles: FileList | File[]) => {
    const fileArray = Array.from(newFiles);
    setPendingFiles((prev) => {
      const updated = [...prev];
      for (const file of fileArray) {
        const error = validateFile(file);
        const isDup = updated.some((p) => p.file.name === file.name && p.file.size === file.size);
        if (!isDup) {
          updated.push({ file, id: `${file.name}-${file.size}-${Date.now()}`, error });
        }
      }
      const validFiles = updated.filter((p) => !p.error).map((p) => p.file);
      onFilesChange(validFiles);
      return updated;
    });
  }, [onFilesChange]);

  const removeFile = (id: string) => {
    setPendingFiles((prev) => {
      const updated = prev.filter((p) => p.id !== id);
      onFilesChange(updated.filter((p) => !p.error).map((p) => p.file));
      return updated;
    });
  };

  return (
    <div className="space-y-3">
      {/* Drop zone */}
      <div
        onDragOver={(e) => { e.preventDefault(); setIsDragging(true); }}
        onDragLeave={() => setIsDragging(false)}
        onDrop={(e) => {
          e.preventDefault();
          setIsDragging(false);
          addFiles(e.dataTransfer.files);
        }}
        onClick={() => !disabled && inputRef.current?.click()}
        className={`
          border-2 border-dashed rounded-lg p-6 text-center cursor-pointer transition-colors
          ${isDragging ? 'border-blue-400 bg-blue-50' : 'border-slate-300 bg-white hover:border-slate-400'}
          ${disabled ? 'opacity-50 cursor-not-allowed' : ''}
        `}
      >
        <Upload className="h-8 w-8 text-slate-400 mx-auto mb-2" />
        <p className="text-sm text-slate-600">
          Drag files here or <span className="text-blue-600 font-medium">browse</span>
        </p>
        <p className="text-xs text-slate-400 mt-1">PDF, DOCX, TXT — max {MAX_SIZE_MB} MB each</p>
        <input
          ref={inputRef}
          type="file"
          multiple
          accept=".pdf,.docx,.txt"
          className="hidden"
          disabled={disabled}
          onChange={(e) => e.target.files && addFiles(e.target.files)}
        />
      </div>

      {/* File list */}
      {pendingFiles.length > 0 && (
        <div className="space-y-2">
          {pendingFiles.map((pf) => (
            <div
              key={pf.id}
              className={`flex items-center gap-3 px-3 py-2 rounded-lg border text-sm ${
                pf.error
                  ? 'border-red-200 bg-red-50'
                  : 'border-slate-200 bg-slate-50'
              }`}
            >
              <span className="shrink-0">{getFileIcon(pf.file.name)}</span>
              <div className="flex-1 min-w-0">
                <p className={`truncate font-medium ${pf.error ? 'text-red-700' : 'text-slate-700'}`}>
                  {pf.file.name}
                </p>
                {pf.error ? (
                  <p className="text-xs text-red-500">{pf.error}</p>
                ) : (
                  <p className="text-xs text-slate-400">{formatBytes(pf.file.size)}</p>
                )}
              </div>
              <Button
                type="button"
                variant="ghost"
                size="icon"
                className="h-6 w-6 shrink-0"
                onClick={(e) => { e.stopPropagation(); removeFile(pf.id); }}
                disabled={disabled}
              >
                <X className="h-3 w-3" />
              </Button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

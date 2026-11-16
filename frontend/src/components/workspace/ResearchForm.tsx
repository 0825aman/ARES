'use client';

import { useState } from 'react';
import { toast } from 'sonner';
import { FlaskConical, Loader2, Network, ArrowRight, ScanSearch, Zap, Terminal, Globe } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { Label } from '@/components/ui/label';
import { Checkbox } from '@/components/ui/checkbox';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { FileUploadArea } from './FileUploadArea';
import { startRun, uploadDocuments } from '@/lib/api/runs';
import { ApiError } from '@/lib/api/client';
import { SUPPORTED_LANGUAGES } from '@/lib/constants/languages';
import type { ResearchRun } from '@/lib/types/run';

interface ResearchFormProps {
  projectId: string;
  defaultQuestion: string;
  onRunStarted: (run: ResearchRun) => void;
}

function parseInitialLanguage(q: string): { cleanQuestion: string; langCode: string } {
  const match = q.match(/\[(?:Target Output Language|Output Language|Target Language|Language):\s*([^\]]+)\]/i);
  if (!match) return { cleanQuestion: q, langCode: 'en' };
  const targetStr = match[1].trim().toLowerCase();
  const found = SUPPORTED_LANGUAGES.find(
    (l) => l.name.toLowerCase() === targetStr || targetStr.includes(l.name.toLowerCase()) || targetStr.includes(l.native.toLowerCase())
  );
  return {
    cleanQuestion: q.replace(/\s*\[(?:Target Output Language|Output Language|Target Language|Language):\s*[^\]]+\]/i, '').trim(),
    langCode: found ? found.code : 'en',
  };
}

export function ResearchForm({ projectId, defaultQuestion, onRunStarted }: ResearchFormProps) {
  const initial = parseInitialLanguage(defaultQuestion);
  const [question, setQuestion] = useState(initial.cleanQuestion);
  const [language, setLanguage] = useState<string>(initial.langCode);
  const [useWeb, setUseWeb] = useState(true);
  const [useDocs, setUseDocs] = useState(false);
  const [workflowMode, setWorkflowMode] = useState<'sequential' | 'multi_agent'>('multi_agent');
  const [verificationDepth, setVerificationDepth] = useState<'basic' | 'thorough'>('basic');
  const [files, setFiles] = useState<File[]>([]);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [sourceError, setSourceError] = useState<string | null>(null);

  const selectedLangObj = SUPPORTED_LANGUAGES.find((l) => l.code === language);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();

    if (!useWeb && !useDocs) {
      setSourceError('Select at least one information source.');
      return;
    }
    if (useDocs && files.length === 0) {
      setSourceError('Upload at least one document when using document research.');
      return;
    }
    setSourceError(null);

    if (!question.trim()) {
      toast.error('Research question is required.');
      return;
    }

    setIsSubmitting(true);
    try {
      let documentIds: string[] = [];

      if (useDocs && files.length > 0) {
        const uploadResult = await uploadDocuments(projectId, files);
        if (uploadResult.uploaded.length === 0) {
          toast.error('All files were rejected. Please check the file format.');
          return;
        }
        documentIds = uploadResult.uploaded.map((d) => d.id);
        if (uploadResult.rejected.length > 0) {
          toast.warning(`${uploadResult.rejected.length} file(s) were rejected and won't be used.`);
        }
      }

      const finalQuestion =
        language !== 'en' && selectedLangObj
          ? `${question.trim()}\n\n[Target Output Language: ${selectedLangObj.name} (${selectedLangObj.native})]`
          : question.trim();

      const run = await startRun(projectId, {
        research_question: finalQuestion,
        use_web: useWeb,
        use_documents: useDocs && documentIds.length > 0,
        document_ids: documentIds,
        workflow_mode: workflowMode,
        verification_depth: verificationDepth,
      });

      toast.success('Research mission dispatched successfully.');
      onRunStarted(run);
    } catch (err) {
      const msg = err instanceof ApiError ? err.message : 'Failed to start research. Please try again.';
      toast.error(msg);
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <Card className="tech-panel border-slate-700 bg-slate-900 shadow-2xl relative overflow-hidden">
      {/* Top subtle glow line */}
      <div className="absolute top-0 left-0 right-0 h-[2px] bg-gradient-to-r from-transparent via-blue-500/60 to-transparent" />

      <CardHeader className="pb-3 border-b border-slate-800">
        <CardTitle className="font-mono text-sm font-bold text-white flex items-center gap-2">
          <Terminal className="h-4 w-4 text-blue-400" />
          DISPATCH AUTONOMOUS SWARM MISSION
        </CardTitle>
        <CardDescription className="font-mono text-xs text-slate-300 font-medium">
          Configure multi-agent coordination parameters and information retrieval channels.
        </CardDescription>
      </CardHeader>
      <CardContent className="pt-5">
        <form onSubmit={handleSubmit} noValidate className="space-y-5">
          {/* Research question */}
          <div className="space-y-1.5">
            <Label htmlFor="research-question" className="font-mono text-xs font-bold text-slate-200">
              Investigation Objective Query
            </Label>
            <Textarea
              id="research-question"
              rows={3}
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              placeholder="What question should this autonomous swarm investigate?"
              className="resize-none font-mono text-xs bg-slate-950 border-slate-700 text-white font-medium"
              disabled={isSubmitting}
            />
            <div className="flex justify-between font-mono text-xs text-slate-300">
              <span>Primary research hypothesis or target query</span>
              <span>{question.length}/1000</span>
            </div>
          </div>

          {/* Workflow mode */}
          <div className="space-y-2">
            <Label className="font-mono text-xs font-bold text-slate-200">Swarm Architecture Mode</Label>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <button
                type="button"
                onClick={() => setWorkflowMode('multi_agent')}
                disabled={isSubmitting}
                className={`flex flex-col gap-1 rounded-lg border p-3.5 text-left transition-all relative overflow-hidden ${
                  workflowMode === 'multi_agent'
                    ? 'border-violet-500/70 bg-violet-500/20 text-white shadow-[0_0_15px_rgba(139,92,246,0.2)]'
                    : 'border-slate-700 bg-slate-950 text-slate-300 hover:border-slate-600'
                }`}
              >
                <div className="flex items-center justify-between">
                  <span className="flex items-center gap-1.5 font-mono text-xs font-bold text-violet-300">
                    <Network className="h-4 w-4" />
                    Autonomous Multi-Agent Swarm
                  </span>
                  <span className="telemetry-chip font-mono text-[10px] text-violet-200 border-violet-500/40 bg-violet-500/20 font-bold">
                    RECOMMENDED
                  </span>
                </div>
                <span className="text-xs text-slate-200 mt-1 leading-snug font-normal">
                  4-node cooperative state machine: Planner ➔ Researcher ➔ Supervisor ➔ Critic.
                </span>
              </button>

              <button
                type="button"
                onClick={() => setWorkflowMode('sequential')}
                disabled={isSubmitting}
                className={`flex flex-col gap-1 rounded-lg border p-3.5 text-left transition-all ${
                  workflowMode === 'sequential'
                    ? 'border-blue-500/70 bg-blue-500/20 text-white shadow-[0_0_15px_rgba(59,130,246,0.2)]'
                    : 'border-slate-700 bg-slate-950 text-slate-300 hover:border-slate-600'
                }`}
              >
                <span className="flex items-center gap-1.5 font-mono text-xs font-bold text-blue-300">
                  <ArrowRight className="h-4 w-4" />
                  Sequential Single-Pass
                </span>
                <span className="text-xs text-slate-200 mt-1 leading-snug font-normal">
                  Linear single-pass research workflow with basic citation generation.
                </span>
              </button>
            </div>
          </div>

          {/* Source selection */}
          <div className="space-y-2">
            <Label className="font-mono text-xs font-bold text-slate-200">Retrieval Channels</Label>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <label
                htmlFor="use-web"
                className={`flex items-center gap-3 p-3.5 rounded-lg border cursor-pointer transition-colors ${
                  useWeb
                    ? 'border-blue-500/50 bg-blue-500/15 text-white'
                    : 'border-slate-700 bg-slate-950 text-slate-300'
                }`}
              >
                <Checkbox
                  id="use-web"
                  checked={useWeb}
                  onCheckedChange={(v) => {
                    setUseWeb(!!v);
                    setSourceError(null);
                  }}
                  disabled={isSubmitting}
                />
                <div className="text-xs font-mono">
                  <p className="font-bold text-white text-xs">Live Web Retrieval</p>
                  <p className="text-xs text-slate-300 font-medium mt-0.5">Query search engines &amp; public documentation</p>
                </div>
              </label>

              <label
                htmlFor="use-docs"
                className={`flex items-center gap-3 p-3.5 rounded-lg border cursor-pointer transition-colors ${
                  useDocs
                    ? 'border-blue-500/50 bg-blue-500/15 text-white'
                    : 'border-slate-700 bg-slate-950 text-slate-300'
                }`}
              >
                <Checkbox
                  id="use-docs"
                  checked={useDocs}
                  onCheckedChange={(v) => {
                    setUseDocs(!!v);
                    setSourceError(null);
                  }}
                  disabled={isSubmitting}
                />
                <div className="text-xs font-mono">
                  <p className="font-bold text-white text-xs">Local Knowledge Ingestion</p>
                  <p className="text-xs text-slate-300 font-medium mt-0.5">Process uploaded PDFs and reference documents</p>
                </div>
              </label>
            </div>
            {sourceError && (
              <p className="font-mono text-xs text-red-400 font-semibold pt-1">{sourceError}</p>
            )}
          </div>

          {/* File upload */}
          {useDocs && (
            <div className="space-y-1.5 pt-1">
              <Label className="font-mono text-xs font-bold text-slate-200">Upload Target Documents</Label>
              <FileUploadArea onFilesChange={setFiles} disabled={isSubmitting} />
            </div>
          )}

          {/* Verification depth */}
          <div className="space-y-2">
            <Label className="font-mono text-xs font-bold text-slate-200">Grounding &amp; Claim Verification</Label>
            <div className="grid grid-cols-2 gap-3">
              <button
                type="button"
                onClick={() => setVerificationDepth('basic')}
                disabled={isSubmitting}
                className={`flex flex-col gap-1 rounded-lg border p-3 text-left transition-colors ${
                  verificationDepth === 'basic'
                    ? 'border-slate-600 bg-slate-800 text-white font-bold'
                    : 'border-slate-800 bg-slate-950 text-slate-400 hover:border-slate-700'
                }`}
              >
                <span className="flex items-center gap-1.5 font-mono text-xs font-bold text-slate-100">
                  <Zap className="h-3.5 w-3.5 text-amber-400" />
                  Standard Grounding
                </span>
                <span className="text-xs text-slate-300 font-normal">
                  Verifies key findings &amp; high-impact claims
                </span>
              </button>
              <button
                type="button"
                onClick={() => setVerificationDepth('thorough')}
                disabled={isSubmitting}
                className={`flex flex-col gap-1 rounded-lg border p-3 text-left transition-colors ${
                  verificationDepth === 'thorough'
                    ? 'border-slate-600 bg-slate-800 text-white font-bold'
                    : 'border-slate-800 bg-slate-950 text-slate-400 hover:border-slate-700'
                }`}
              >
                <span className="flex items-center gap-1.5 font-mono text-xs font-bold text-slate-100">
                  <ScanSearch className="h-3.5 w-3.5 text-cyan-400" />
                  Adversarial Deep Scan
                </span>
                <span className="text-xs text-slate-300 font-normal">
                  Full atomic claim extraction with cross-critic verification
                </span>
              </button>
            </div>
          </div>

          {/* Research Output Language */}
          <div className="space-y-1.5">
            <Label htmlFor="run_language" className="font-mono text-xs font-bold text-slate-200 flex items-center gap-1.5">
              <Globe className="h-3.5 w-3.5 text-blue-400" />
              <span>Research Output Language</span>
            </Label>
            <Select value={language} onValueChange={setLanguage}>
              <SelectTrigger id="run_language" className="bg-slate-950 border-slate-700 font-mono text-xs text-white">
                <SelectValue placeholder="Select output language" />
              </SelectTrigger>
              <SelectContent className="max-h-64 bg-slate-900 border-slate-800 text-slate-200">
                {SUPPORTED_LANGUAGES.map((lang) => (
                  <SelectItem key={lang.code} value={lang.code} className="text-xs font-mono">
                    <span className="font-semibold text-white">{lang.name}</span>{' '}
                    <span className="text-slate-400">({lang.native})</span>
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            {language !== 'en' && selectedLangObj && (
              <p className="text-[11px] font-mono text-sky-300">
                Synthesis Directive: Report, evidence analysis, and executive summary will be generated in <strong>{selectedLangObj.name} ({selectedLangObj.native})</strong>.
              </p>
            )}
          </div>

          {/* Submit */}
          <div className="flex justify-end pt-3 border-t border-slate-800">
            <Button
              type="submit"
              disabled={isSubmitting}
              className="bg-blue-600 hover:bg-blue-500 text-white font-mono text-xs font-bold border border-blue-400/40 shadow-lg shadow-blue-500/25 px-5 py-2"
            >
              {isSubmitting ? (
                <>
                  <Loader2 className="h-3.5 w-3.5 mr-2 animate-spin" />
                  DISPATCHING SWARM…
                </>
              ) : (
                <>
                  <FlaskConical className="h-3.5 w-3.5 mr-2" />
                  DISPATCH MISSION
                </>
              )}
            </Button>
          </div>
        </form>
      </CardContent>
    </Card>
  );
}

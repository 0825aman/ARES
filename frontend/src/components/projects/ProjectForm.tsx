'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { toast } from 'sonner';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Label } from '@/components/ui/label';
import { Loader2, Globe } from 'lucide-react';
import { createProject } from '@/lib/api/projects';
import { PROJECT_CATEGORIES } from '@/lib/constants/categories';
import { SUPPORTED_LANGUAGES } from '@/lib/constants/languages';
import { ApiError } from '@/lib/api/client';

interface FieldErrors {
  title?: string;
  research_question?: string;
  description?: string;
}

export function ProjectForm() {
  const router = useRouter();
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errors, setErrors] = useState<FieldErrors>({});

  const [title, setTitle] = useState('');
  const [researchQuestion, setResearchQuestion] = useState('');
  const [description, setDescription] = useState('');
  const [category, setCategory] = useState<string>('');
  const [language, setLanguage] = useState<string>('en');

  const selectedLangObj = SUPPORTED_LANGUAGES.find((l) => l.code === language);

  function validate(): FieldErrors {
    const errs: FieldErrors = {};
    if (!title.trim()) errs.title = 'Research title is required.';
    else if (title.trim().length > 200) errs.title = 'Title must be 200 characters or fewer.';
    if (!researchQuestion.trim()) errs.research_question = 'Research question is required.';
    else if (researchQuestion.trim().length > 1000)
      errs.research_question = 'Research question must be 1000 characters or fewer.';
    if (description.length > 2000)
      errs.description = 'Description must be 2000 characters or fewer.';
    return errs;
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const validationErrors = validate();
    if (Object.keys(validationErrors).length > 0) {
      setErrors(validationErrors);
      return;
    }
    setErrors({});
    setIsSubmitting(true);
    try {
      const finalQuestion =
        language !== 'en' && selectedLangObj
          ? `${researchQuestion.trim()}\n\n[Target Output Language: ${selectedLangObj.name} (${selectedLangObj.native})]`
          : researchQuestion.trim();

      const project = await createProject({
        title: title.trim(),
        research_question: finalQuestion,
        description: description.trim() || null,
        category: (category || null) as never,
      });
      toast.success('Research project created successfully.');
      router.push(`/projects/${project.id}`);
      router.refresh();
    } catch (err) {
      const message = err instanceof ApiError ? err.message : 'Something went wrong. Please try again.';
      toast.error(message);
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} noValidate className="space-y-6">
      {/* Title */}
      <div className="space-y-1.5">
        <Label htmlFor="title">
          Research Title <span className="text-destructive">*</span>
        </Label>
        <Input
          id="title"
          placeholder="e.g. Impact of AI on Healthcare Diagnostics"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          onBlur={() => {
            if (!title.trim()) setErrors((p) => ({ ...p, title: 'Research title is required.' }));
            else setErrors((p) => ({ ...p, title: undefined }));
          }}
          aria-invalid={!!errors.title}
          className={errors.title ? 'border-destructive' : ''}
        />
        {errors.title && <p className="text-xs text-destructive">{errors.title}</p>}
      </div>

      {/* Research Question */}
      <div className="space-y-1.5">
        <Label htmlFor="research_question">
          Research Question <span className="text-destructive">*</span>
        </Label>
        <Textarea
          id="research_question"
          placeholder="What specific question is this research trying to answer?"
          rows={4}
          value={researchQuestion}
          onChange={(e) => setResearchQuestion(e.target.value)}
          onBlur={() => {
            if (!researchQuestion.trim())
              setErrors((p) => ({ ...p, research_question: 'Research question is required.' }));
            else setErrors((p) => ({ ...p, research_question: undefined }));
          }}
          aria-invalid={!!errors.research_question}
          className={errors.research_question ? 'border-destructive' : ''}
        />
        {errors.research_question && (
          <p className="text-xs text-destructive">{errors.research_question}</p>
        )}
      </div>

      {/* Description */}
      <div className="space-y-1.5">
        <Label htmlFor="description">Description (optional)</Label>
        <Textarea
          id="description"
          placeholder="Provide additional context or background..."
          rows={3}
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          aria-invalid={!!errors.description}
          className={errors.description ? 'border-destructive' : ''}
        />
        {errors.description && <p className="text-xs text-destructive">{errors.description}</p>}
      </div>

      {/* Category and Language Selection */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        {/* Category */}
        <div className="space-y-1.5">
          <Label htmlFor="category">Category</Label>
          <Select value={category} onValueChange={setCategory}>
            <SelectTrigger id="category" className="bg-slate-900 border-slate-700">
              <SelectValue placeholder="Select a category" />
            </SelectTrigger>
            <SelectContent className="bg-slate-900 border-slate-800 text-slate-200">
              {PROJECT_CATEGORIES.map((cat) => (
                <SelectItem key={cat} value={cat}>
                  {cat}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        {/* Target Research Language */}
        <div className="space-y-1.5">
          <Label htmlFor="language" className="flex items-center gap-1.5">
            <Globe className="h-3.5 w-3.5 text-blue-400" />
            <span>Research Output Language</span>
          </Label>
          <Select value={language} onValueChange={setLanguage}>
            <SelectTrigger id="language" className="bg-slate-900 border-slate-700 font-mono text-xs">
              <SelectValue placeholder="Select language" />
            </SelectTrigger>
            <SelectContent className="max-h-72 bg-slate-900 border-slate-800 text-slate-200">
              {SUPPORTED_LANGUAGES.map((lang) => (
                <SelectItem key={lang.code} value={lang.code} className="text-xs font-mono">
                  <span className="font-semibold text-white">{lang.name}</span>{' '}
                  <span className="text-slate-400">({lang.native})</span>
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      </div>

      {/* Target Language Directive Indicator */}
      {language !== 'en' && selectedLangObj && (
        <div className="rounded-lg border border-blue-500/40 bg-blue-950/30 p-3 text-xs font-mono text-blue-300 flex items-start gap-2.5 shadow-sm">
          <Globe className="h-4 w-4 text-blue-400 shrink-0 mt-0.5" />
          <div className="space-y-0.5">
            <p className="font-semibold text-sky-200">
              Multi-Lingual Synthesis Directive: {selectedLangObj.name} ({selectedLangObj.native})
            </p>
            <p className="text-[11px] text-slate-300 leading-relaxed">
              The autonomous swarm will retrieve global cross-lingual evidence and synthesize the final report, key findings, and executive summary directly in <strong>{selectedLangObj.name}</strong>.
            </p>
          </div>
        </div>
      )}

      {/* Actions */}
      <div className="flex items-center justify-end gap-3 pt-2">
        <Button
          type="button"
          variant="ghost"
          onClick={() => router.push('/projects')}
          disabled={isSubmitting}
        >
          Cancel
        </Button>
        <Button type="submit" disabled={isSubmitting}>
          {isSubmitting ? (
            <>
              <Loader2 className="h-4 w-4 mr-2 animate-spin" />
              Creating…
            </>
          ) : (
            'Create Research →'
          )}
        </Button>
      </div>
    </form>
  );
}

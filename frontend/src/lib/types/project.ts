export type ProjectStatus = 'not_started' | 'in_progress' | 'completed' | 'archived';

export type ProjectCategory =
  | 'Technology'
  | 'Science'
  | 'Business'
  | 'Health & Medicine'
  | 'Society & Culture'
  | 'Environment'
  | 'Economics'
  | 'History'
  | 'Law & Policy'
  | 'Other';

export interface Project {
  id: string;
  title: string;
  research_question: string;
  description: string | null;
  category: ProjectCategory | null;
  status: ProjectStatus;
  created_at: string;
  updated_at: string;
}

export interface ProjectBrief {
  id: string;
  title: string;
  category: ProjectCategory | null;
  status: ProjectStatus;
  created_at: string;
}

export interface ProjectListResponse {
  items: Project[];
  total: number;
  limit: number;
  offset: number;
}

export interface ProjectSummaryResponse {
  total: number;
  by_status: Record<ProjectStatus, number>;
  recent_projects: ProjectBrief[];
}

export interface CreateProjectInput {
  title: string;
  research_question: string;
  description?: string | null;
  category?: ProjectCategory | null;
}

export interface UpdateProjectInput {
  title?: string;
  research_question?: string;
  description?: string | null;
  category?: ProjectCategory | null;
  status?: ProjectStatus;
}

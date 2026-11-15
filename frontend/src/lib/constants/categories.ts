export const PROJECT_CATEGORIES = [
  'Technology',
  'Science',
  'Business',
  'Health & Medicine',
  'Society & Culture',
  'Environment',
  'Economics',
  'History',
  'Law & Policy',
  'Other',
] as const;

export type ProjectCategoryValue = typeof PROJECT_CATEGORIES[number];

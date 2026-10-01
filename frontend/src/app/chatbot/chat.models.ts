/**
 * llm: written by the model; offline: raw matching content (model unavailable);
 * not_found: outside the knowledge base; export: a file request for the previous answer.
 */
export type ChatMode = 'llm' | 'offline' | 'not_found' | 'export';

export type ChartType = 'line' | 'bar' | 'doughnut';
export type ExportFormat = 'pdf' | 'pptx';

/** Built by charts.py; every number comes from the knowledge base. */
export interface ChartSpec {
  type: ChartType;
  title: string;
  unit: string;
  labels: string[];
  series: { name: string; values: (number | null)[] }[];
  source?: string;
}

export interface ChatProfile {
  profession?: string;
  age?: string;
  education?: string;
  familiarity?: string;
}

export interface Source {
  title: string;
  url: string;
}

export interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
  sources?: Source[];
  mode?: ChatMode;
  chart?: ChartSpec;
  /** The question this message answers (used as the title of exported files). */
  question?: string;
  /** Quick-reply chips shown under a bot message (used during onboarding). */
  options?: string[];
}

export interface ChatResponse {
  answer: string;
  sources: Source[];
  mode: ChatMode;
  chart?: ChartSpec;
  /** The user asked for this answer (or, with export_previous, the previous one) as a file. */
  export?: ExportFormat;
  export_previous?: boolean;
}

export interface ExportRequest {
  format: ExportFormat;
  title: string;
  answer: string;
  sources: Source[];
  chart?: ChartSpec;
  chart_png?: string | null;
}

export interface OnboardingStep {
  key: keyof ChatProfile;
  question: string;
  options: string[];
  /** Allow a typed answer as well as the chips. */
  freeText?: boolean;
}

/** Asked one at a time before the first question. Option labels must match rag.py. */
export const ONBOARDING_STEPS: OnboardingStep[] = [
  {
    key: 'profession',
    question: 'First, what best describes your profession or role?',
    options: [
      'Student',
      'Teacher / Educator',
      'Parent',
      'Researcher / Analyst',
      'Policymaker / Government',
      'Journalist',
      'Nonprofit / Community',
    ],
    freeText: true,
  },
  {
    key: 'age',
    question: 'Which age group are you in?',
    options: ['Under 13', '13-17', '18-24', '25-44', '45-64', '65+'],
  },
  {
    key: 'education',
    question: "What's the highest level of education you've completed (or are in now)?",
    options: [
      'Middle school or below',
      'High school',
      'Some college / Associate',
      "Bachelor's degree",
      'Master\'s / Doctorate',
    ],
  },
  {
    key: 'familiarity',
    question: 'Last one: how comfortable are you working with data?',
    options: ['New to data', 'Some experience', 'Data expert'],
  },
];

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
  mode?: 'llm' | 'offline';
  /** Quick-reply chips shown under a bot message (used during onboarding). */
  options?: string[];
}

export interface ChatResponse {
  answer: string;
  sources: Source[];
  mode: 'llm' | 'offline';
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

export const SUGGESTED_QUESTIONS = [
  'Where can I find four-year graduation rates?',
  'What data do you have on chronic absenteeism?',
  'Tell me about student loan debt in Connecticut',
  'What is the PSEO data?',
  'How can I see Smarter Balanced test results?',
];

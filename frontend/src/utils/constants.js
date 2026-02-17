export const API_BASE = '/api'

export const MODEL_COLORS = {
  'claude-3.5-sonnet': { bg: 'bg-orange-500/20', text: 'text-orange-400', border: 'border-orange-500/30', hex: '#F97316' },
  'gpt-4o':            { bg: 'bg-green-500/20',  text: 'text-green-400',  border: 'border-green-500/30',  hex: '#22C55E' },
  'gemini-1.5-pro':    { bg: 'bg-blue-500/20',   text: 'text-blue-400',   border: 'border-blue-500/30',   hex: '#3B82F6' },
  'deepseek-v3':       { bg: 'bg-purple-500/20',  text: 'text-purple-400', border: 'border-purple-500/30', hex: '#A855F7' },
  'gpt-4o-mini':       { bg: 'bg-emerald-500/20', text: 'text-emerald-400',border: 'border-emerald-500/30',hex: '#34D399' },
  'claude-3-haiku':    { bg: 'bg-amber-500/20',   text: 'text-amber-400',  border: 'border-amber-500/30',  hex: '#F59E0B' },
}

export const TASK_TYPE_LABELS = {
  code: 'Code',
  creative: 'Creative',
  math: 'Math',
  summarization: 'Summary',
  translation: 'Translation',
  qa: 'Q&A',
  multi_step: 'Multi-Step',
}

export const TASK_TYPE_COLORS = {
  code: 'bg-blue-500/20 text-blue-400',
  creative: 'bg-pink-500/20 text-pink-400',
  math: 'bg-purple-500/20 text-purple-400',
  summarization: 'bg-teal-500/20 text-teal-400',
  translation: 'bg-cyan-500/20 text-cyan-400',
  qa: 'bg-yellow-500/20 text-yellow-400',
  multi_step: 'bg-indigo-500/20 text-indigo-400',
}

export const EXAMPLE_PROMPTS = [
  { text: 'Write a Python function to implement a binary search tree with insert and delete operations', type: 'code' },
  { text: 'Write a short story about a robot learning to paint', type: 'creative' },
  { text: 'Solve the integral of x²·e^x dx using integration by parts', type: 'math' },
  { text: 'Summarize the key principles of clean code architecture', type: 'summarization' },
  { text: 'Translate "The early bird catches the worm" to Japanese, French, and Spanish', type: 'translation' },
  { text: 'What is the difference between TCP and UDP?', type: 'qa' },
  { text: 'Create a step-by-step guide to deploying a full-stack app on AWS', type: 'multi_step' },
]

/**
 * Screenplay Studio Constants
 */

import { ProjectTier, VideoProvider } from './types';

export const TIER_INFO: Record<ProjectTier, {
  name: string;
  description: string;
  features: string[];
  color: string;
  icon: string;
}> = {
  free: {
    name: 'Free',
    description: 'Screenplay generation only',
    features: [
      'Story analysis',
      'Scene breakdown',
      'Dialogue & action writing',
      'Vietnamese adaptation',
      'Fountain & PDF export',
    ],
    color: 'gray',
    icon: 'pen-line',
  },
  standard: {
    name: 'Standard',
    description: 'Add storyboard images',
    features: [
      'Everything in Free',
      'Shot list design',
      'Visual style guides',
      'AI storyboard images',
      'Storyboard PDF export',
    ],
    color: 'blue',
    icon: 'image',
  },
  pro: {
    name: 'Pro',
    description: 'Add video generation',
    features: [
      'Everything in Standard',
      'AI video prompts',
      'Video generation',
      'Basic video editing',
      'Scene videos export',
    ],
    color: 'purple',
    icon: 'clapperboard',
  },
  director: {
    name: 'Director',
    description: 'Full production suite',
    features: [
      'Everything in Pro',
      'Multiple takes per shot',
      'Advanced transitions',
      'Title cards',
      'Final compiled video',
    ],
    color: 'gold',
    icon: 'trophy',
  },
};

export const VIDEO_PROVIDERS: Record<VideoProvider, {
  name: string;
  description: string;
  cost_per_second: number;
  quality: 'budget' | 'balanced' | 'best';
  max_duration: number;
}> = {
  pika: {
    name: 'Pika Labs',
    description: 'Budget-friendly option',
    cost_per_second: 0.02,
    quality: 'budget',
    max_duration: 4,
  },
  runway: {
    name: 'Runway Gen-3',
    description: 'Balanced quality & cost',
    cost_per_second: 0.05,
    quality: 'balanced',
    max_duration: 10,
  },
  veo: {
    name: 'Google Veo 2',
    description: 'Best quality available',
    cost_per_second: 0.08,
    quality: 'best',
    max_duration: 16,
  },
};

export const PHASE_NAMES: Record<number, string> = {
  0: 'Draft',
  1: 'Analysis',
  2: 'Screenplay',
  3: 'Pre-Visualization',
  4: 'Video Rendering',
  5: 'Complete',
};

export const STATUS_COLORS: Record<string, string> = {
  draft: 'gray',
  analyzing: 'blue',
  writing: 'indigo',
  visualizing: 'purple',
  rendering: 'pink',
  completed: 'green',
  failed: 'red',
};

export const MAX_SOURCE_LENGTH = 500000;
export const MIN_SOURCE_LENGTH = 1000;

export const SUPPORTED_LANGUAGES = [
  { code: 'en' as const, name: 'English' },
  { code: 'vi' as const, name: 'Tiếng Việt' },
];

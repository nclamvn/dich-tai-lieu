/**
 * Screenplay Studio TypeScript Types
 */

export type ProjectTier = 'free' | 'standard' | 'pro' | 'director';
export type ProjectStatus = 'draft' | 'analyzing' | 'writing' | 'visualizing' | 'rendering' | 'completed' | 'failed';
export type Language = 'en' | 'vi';
export type VideoProvider = 'runway' | 'veo' | 'pika';

export interface Character {
  name: string;
  role: string;
  description: string;
  traits: string[];
  arc: string;
  age_range?: string;
  relationships: Record<string, string>;
}

export interface SceneHeading {
  int_ext: 'INT' | 'EXT' | 'INT/EXT';
  location: string;
  time: string;
}

export interface DialogueBlock {
  character: string;
  dialogue: string;
  parenthetical?: string;
}

export interface ActionBlock {
  text: string;
}

export type SceneElement = DialogueBlock | ActionBlock;

export interface Scene {
  scene_number: number;
  heading: SceneHeading;
  summary: string;
  characters_present: string[];
  emotional_beat: string;
  elements: SceneElement[];
  page_count?: number;
}

export interface Shot {
  shot_number: string;
  shot_type: string;
  description: string;
  camera_angle: string;
  camera_movement: string;
  duration_seconds: number;
  storyboard_image?: string;
  ai_prompt?: string;
}

export interface ShotList {
  scene_number: number;
  shots: Shot[];
  visual_style: string;
}

export interface StoryAnalysis {
  genre: string;
  themes: string[];
  tone: string;
  setting: string;
  time_period: string;
  characters: Character[];
  logline: string;
  estimated_runtime_minutes: number;
  estimated_scenes: number;
}

export interface Screenplay {
  title: string;
  author: string;
  language: Language;
  scenes: Scene[];
  total_pages: number;
  genre: string;
  logline: string;
}

export interface ScreenplayProject {
  id: string;
  user_id: string;
  title: string;
  source_text: string;
  language: Language;
  tier: ProjectTier;
  status: ProjectStatus;
  story_analysis?: StoryAnalysis;
  screenplay?: Screenplay;
  shot_lists?: ShotList[];
  storyboard_images?: string[];
  video_provider?: VideoProvider;
  video_clips?: string[];
  final_video?: string;
  estimated_cost_usd: number;
  actual_cost_usd: number;
  current_phase: number;
  progress_percent: number;
  error_message?: string;
  output_files: {
    screenplay_fountain?: string;
    screenplay_pdf?: string;
    storyboard_pdf?: string;
    video_final?: string;
  };
  created_at: string;
  updated_at: string;
  completed_at?: string;
}

export interface ProjectListResponse {
  projects: ScreenplayProject[];
  total: number;
  page: number;
  page_size: number;
}

export interface CostEstimate {
  tier: ProjectTier;
  provider?: VideoProvider;
  estimated_scenes: number;
  estimated_pages: number;
  costs: {
    screenplay: number;
    storyboard: number;
    video: number;
    total: number;
  };
}

export interface GenerationProgress {
  project_id: string;
  status: ProjectStatus;
  current_phase: number;
  progress_percent: number;
  message: string;
  estimated_time_remaining?: number;
}

export interface CreateProjectInput {
  title: string;
  source_text: string;
  language: Language;
  tier: ProjectTier;
  video_provider?: VideoProvider;
}

export interface UpdateProjectInput {
  title?: string;
  tier?: ProjectTier;
  video_provider?: VideoProvider;
}


export enum Category {
  PEOPLE = '人物',
  ANIMALS = '动物',
  MACHINES = '机械',
  PLANTS = '植物',
  FLAME = '火焰',
  ARCHITECTURE = '建筑',
  ENVIRONMENT = '环境'
}

export type AspectRatio = '1:1' | '3:4' | '4:3' | '9:16' | '16:9' | '2:3' | '3:2' | '21:9';
export type Resolution = '360p' | '480p' | '720p' | '1080p' | '2K' | '4K';

export type ModelProvider = 'google' | 'aliyun';

export interface ModelInfo {
  id: string;
  name: string;
  provider: ModelProvider;
  modelName: string;
  description: string;
}

export interface GeneratedImage {
  id: string;
  url: string;
  originalUrl?: string;
  category: string;
  prompt: string;
  timestamp: number;
  filename?: string;
}

export interface BatchProgress {
  total: number;
  current: number;
  category: string | null;
  status: 'idle' | 'running' | 'completed' | 'error';
}

export interface ProductionConfig {
  commonSubject: string;
  globalStyle: string;
  negativePrompt: string;
  categoryPrompts: Record<string, string>;
  aspectRatio: AspectRatio;
  resolution: Resolution;
  countPerCategory: number;
}

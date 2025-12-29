import React from 'react';
import { AspectRatio, Resolution, ModelInfo } from '../types';

interface SettingsPageProps {
  commonSubject: string;
  setCommonSubject: (v: string) => void;
  aspectRatio: AspectRatio;
  setAspectRatio: (v: AspectRatio) => void;
  resolution: Resolution;
  setResolution: (v: Resolution) => void;
  categories: string[];
  selectedCategories: Set<string>;
  editingCategory: string;
  setEditingCategory: (v: string) => void;
  catPrompts: Record<string, string>;
  setCatPrompts: (v: Record<string, string>) => void;
  handleCategoryClick: (cat: string) => void;
  handleAddCustomCategory: () => void;
  handleTranslate: (type: 'common' | 'category') => void;
  isTranslating: string | null;
  countPerCategory: number;
  setCountPerCategory: (n: number) => void;
  modelLimit?: number;
  startGeneration: () => void;
  progressStatus: 'idle' | 'running' | 'completed' | 'error';
  selectedModel: ModelInfo;
  setSelectedModel: (m: ModelInfo) => void;
  models: ModelInfo[];
  stopNow: () => void;
}

export const SettingsPage: React.FC<SettingsPageProps> = ({
  commonSubject,
  setCommonSubject,
  aspectRatio,
  setAspectRatio,
  resolution,
  setResolution,
  categories,
  selectedCategories,
  editingCategory,
  setEditingCategory,
  catPrompts,
  setCatPrompts,
  handleCategoryClick,
  handleAddCustomCategory,
  handleTranslate,
  isTranslating,
  countPerCategory,
  setCountPerCategory,
  modelLimit,
  startGeneration,
  progressStatus,
  selectedModel,
  setSelectedModel,
  models,
  stopNow
}) => {
  return (
    <div className="space-y-6">
      <div className="space-y-4">
        <div className="relative group">
          <label className="text-[10px] font-bold text-zinc-500 uppercase tracking-widest block mb-2">通用基础主体</label>
          <div className="relative">
            <textarea
              value={commonSubject}
              onChange={(e) => setCommonSubject(e.target.value)}
              className="w-full bg-black border border-zinc-800 rounded-lg p-3 pr-10 text-xs min-h-[80px] focus:border-blue-500 outline-none transition-all resize-none shadow-inner"
            />
            <button
              onClick={() => handleTranslate('common')}
              disabled={isTranslating === 'common'}
              className="absolute bottom-3 right-3 p-2 bg-zinc-800 hover:bg-blue-600 rounded-lg transition-all border border-zinc-700 hover:border-blue-400 group/btn"
              title="中英互译"
            >
              {isTranslating === 'common' ? (
                <div className="w-3 h-3 border-2 border-white/20 border-t-white rounded-full animate-spin" />
              ) : (
                <span className="text-[10px] font-bold text-zinc-400 group-hover/btn:text-white">文/A</span>
              )}
            </button>
          </div>
        </div>
        <div className="grid grid-cols-2 gap-4">
          <div className="space-y-2">
            <label className="text-[9px] font-bold text-zinc-600 uppercase">比例</label>
            <select
              value={aspectRatio}
              onChange={(e) => setAspectRatio(e.target.value as AspectRatio)}
              className="w-full bg-zinc-900 border border-zinc-800 rounded px-2 py-1.5 text-[10px] outline-none"
            >
              <option value="16:9">16:9 (Cinematic)</option>
              <option value="21:9">21:9 (Ultrawide)</option>
              <option value="3:2">3:2 (Landscape)</option>
              <option value="4:3">4:3 (TV)</option>
              <option value="1:1">1:1 (Square)</option>
              <option value="3:4">3:4 (Portrait)</option>
              <option value="2:3">2:3 (Classic)</option>
              <option value="9:16">9:16 (Vertical)</option>
            </select>
          </div>
          <div className="space-y-2">
            <label className="text-[9px] font-bold text-zinc-600 uppercase">画质 (Google)</label>
            <select
              value={resolution}
              onChange={(e) => setResolution(e.target.value as Resolution)}
              className="w-full bg-zinc-900 border border-zinc-800 rounded px-2 py-1.5 text-[10px] outline-none"
            >
              <option value="360p">360p (SD)</option>
              <option value="480p">480p (SD)</option>
              <option value="720p">720p (HD)</option>
              <option value="1080p">1080p (Full HD)</option>
              <option value="2K">2K (QHD)</option>
              <option value="4K">4K (UHD)</option>
            </select>
          </div>
        </div>
      </div>

      <div className="space-y-3">
        <label className="text-[10px] font-bold text-zinc-500 uppercase tracking-widest block">生产分类</label>
        <div className="flex flex-wrap gap-1.5">
          {categories.map(cat => (
            <button
              key={cat}
              onClick={() => handleCategoryClick(cat)}
              className={`px-3 py-1.5 text-[11px] font-bold rounded border transition-all ${selectedCategories.has(cat) ? 'bg-blue-600 text-white border-blue-400' : 'bg-zinc-800 text-zinc-500 border-transparent hover:bg-zinc-700'}`}
            >
              {cat}
            </button>
          ))}
          <button
            onClick={handleAddCustomCategory}
            className="px-3 py-1.5 text-[11px] font-black rounded border border-dashed border-zinc-700 text-zinc-500 hover:border-blue-500 hover:text-blue-400 transition-all bg-transparent"
          >
            + 自定义
          </button>
        </div>
        <div className="relative">
          <textarea
            value={catPrompts[editingCategory] || ''}
            onChange={(e) => setCatPrompts({ ...catPrompts, [editingCategory]: e.target.value })}
            className="w-full bg-black border border-zinc-800 rounded-lg p-3 pr-10 text-xs min-h-[100px] outline-none transition-all focus:border-blue-500"
            placeholder={`编辑 ${editingCategory} 描述...`}
          />
          <button
            onClick={() => handleTranslate('category')}
            disabled={isTranslating === 'category'}
            className="absolute bottom-3 right-3 p-2 bg-zinc-800 hover:bg-blue-600 rounded-lg transition-all border border-zinc-700 hover:border-blue-400 group/btn"
            title="中英互译"
          >
            {isTranslating === 'category' ? (
              <div className="w-3 h-3 border-2 border-white/20 border-t-white rounded-full animate-spin" />
            ) : (
              <span className="text-[10px] font-bold text-zinc-400 group-hover/btn:text-white">文/A</span>
            )}
          </button>
        </div>
      </div>

      <div className="pt-4 border-t border-zinc-800 space-y-4">
        <div className="grid grid-cols-2 gap-4 items-end">
          <div>
            <label className="text-[10px] font-bold text-zinc-500 uppercase tracking-widest block mb-2">每类数量</label>
            <input
              type="number"
              value={countPerCategory}
              min={1}
              max={modelLimit ?? undefined}
              onChange={(e) => setCountPerCategory(parseInt(e.target.value) || 1)}
              className="w-full bg-black border border-zinc-800 rounded p-2 text-xs outline-none"
            />
          </div>
          <div className="text-right text-[10px] font-black text-blue-400 uppercase">
            预计生成: {selectedCategories.size * countPerCategory} 张{typeof modelLimit === 'number' ? ` · 上限 ${modelLimit}` : ''}
          </div>
        </div>

        <div className="space-y-3">
          <button
            onClick={startGeneration}
            disabled={progressStatus === 'running' || selectedCategories.size === 0}
            className={`w-full py-4 rounded-xl text-xs font-black uppercase tracking-widest transition-all ${progressStatus === 'running' ? 'bg-zinc-900 text-zinc-700' : 'bg-blue-600 text-white hover:bg-blue-500 shadow-lg shadow-blue-900/20'}`}
          >
            {progressStatus === 'running' ? '正在执行任务流...' : `启动批量生产 (已选 ${selectedCategories.size})`}
          </button>

          <div className="space-y-2">
            <label className="text-[9px] font-black text-zinc-500 uppercase tracking-tighter block text-center">AI 模型选择 (Model Selection)</label>
            <div className="relative group">
              <select
                value={selectedModel.id}
                onChange={(e) => setSelectedModel(models.find(m => m.id === e.target.value) || models[0])}
                className="w-full appearance-none bg-[#1a1c20] border border-zinc-800 group-hover:border-blue-500/50 rounded-lg px-4 py-3 text-[11px] font-mono font-bold text-zinc-300 outline-none transition-all cursor-pointer shadow-xl"
              >
                {models.map(m => (
                  <option key={m.id} value={m.id}>[{m.provider.toUpperCase()}] {m.name}</option>
                ))}
              </select>
              <div className="absolute inset-y-0 right-3 flex items-center pointer-events-none text-zinc-600 group-hover:text-blue-400">
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2.5" d="M19 9l-7 7-7-7"></path></svg>
              </div>
            </div>
            <p className="text-[9px] text-zinc-600 text-center font-medium italic">{selectedModel.description}</p>
          </div>

          {progressStatus === 'running' && (
            <button onClick={stopNow} className="w-full py-2 text-[10px] font-bold text-red-500 uppercase hover:text-red-400 transition-colors">
              紧急停止作业
            </button>
          )}
        </div>
      </div>
    </div>
  );
};

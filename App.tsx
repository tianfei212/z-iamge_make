
import React, { useState, useCallback, useRef } from 'react';
import { Category, GeneratedImage, BatchProgress, AspectRatio, Resolution, ModelInfo } from './types';
import { geminiService } from './services/geminiService';
import { ImageCard } from './components/ImageCard';
import JSZip from 'jszip';

const MODELS: ModelInfo[] = [
  {
    id: 'aliyun-wan-v2.1',
    name: 'Aliyun Wan-v2.1',
    provider: 'aliyun',
    modelName: 'wan-v2.1-t2i-14b',
    description: 'Bailian High-Performance Generation'
  },
  {
    id: 'gemini-flash',
    name: 'Gemini 2.5 Flash',
    provider: 'google',
    modelName: 'gemini-2.5-flash-image',
    description: 'Fast & Efficient'
  },
  {
    id: 'gemini-pro',
    name: 'Gemini 3 Pro',
    provider: 'google',
    modelName: 'gemini-3-pro-image-preview',
    description: 'High Quality & Detail'
  }
];

const INITIAL_CATEGORIES = Object.values(Category);

const INITIAL_PROMPTS: Record<string, string> = {
  [Category.PEOPLE]: "特写肖像，动态姿势，服饰质感极其写实",
  [Category.ANIMALS]: "自然栖息地中的生物，极具张力的动作瞬间",
  [Category.MACHINES]: "复杂的内部结构外露，蓝图感与实物结合",
  [Category.PLANTS]: "带有魔幻感的植物形态，微观纹理与生物发光",
  [Category.FLAME]: "不同色温混合的火焰，粒子飞溅与烟雾效果",
  [Category.ARCHITECTURE]: "未来主义建筑，几何空间，冷淡材质",
  [Category.ENVIRONMENT]: "宏大的地貌景观，史诗感的大气效果"
};

const App: React.FC = () => {
  const [commonSubject, setCommonSubject] = useState('未来主义科技都市，雨夜，霓虹灯光');
  const [globalStyle, setGlobalStyle] = useState('电影级写实摄影，极高动态范围，徕卡色调');
  const [negativePrompt, setNegativePrompt] = useState('文字，水印，签名，模糊，重影，低对比度，畸形肢体');
  const [countPerCategory, setCountPerCategory] = useState<number>(20);
  const [aspectRatio, setAspectRatio] = useState<AspectRatio>('16:9');
  const [resolution, setResolution] = useState<Resolution>('1K');
  
  const [selectedModel, setSelectedModel] = useState<ModelInfo>(MODELS[0]);
  const [categories, setCategories] = useState<string[]>(INITIAL_CATEGORIES);
  const [selectedCategories, setSelectedCategories] = useState<Set<string>>(new Set(INITIAL_CATEGORIES));
  const [editingCategory, setEditingCategory] = useState<string>(Category.PEOPLE);
  const [catPrompts, setCatPrompts] = useState<Record<string, string>>(INITIAL_PROMPTS);
  
  const [images, setImages] = useState<GeneratedImage[]>([]);
  const [logs, setLogs] = useState<string[]>([]);
  const [isZipping, setIsZipping] = useState(false);
  const [isTranslating, setIsTranslating] = useState<string | null>(null);

  const [progress, setProgress] = useState<BatchProgress>({
    total: 0,
    current: 0,
    category: null,
    status: 'idle'
  });
  
  const isStopping = useRef(false);

  const addLog = (msg: string) => {
    setLogs(prev => [`[${new Date().toLocaleTimeString()}] ${msg}`, ...prev].slice(0, 100));
  };

  const handleTranslate = async (type: 'common' | 'category') => {
    const text = type === 'common' ? commonSubject : catPrompts[editingCategory];
    if (!text || isTranslating) return;

    setIsTranslating(type);
    addLog(`正在翻译 ${type === 'common' ? '通用主体' : '分类提示词'}...`);
    try {
      const translated = await geminiService.translateText(text);
      if (type === 'common') setCommonSubject(translated);
      else setCatPrompts({ ...catPrompts, [editingCategory]: translated });
      addLog('翻译完成。');
    } catch (e) {
      addLog('翻译请求失败。');
    } finally {
      setIsTranslating(null);
    }
  };

  const handleCategoryClick = (cat: string) => {
    setEditingCategory(cat);
    setSelectedCategories(prev => {
      const next = new Set(prev);
      if (next.has(cat)) next.delete(cat);
      else next.add(cat);
      return next;
    });
  };

  const handleAddCustomCategory = () => {
    const name = window.prompt("请输入自定义分类名称 (例如: 家具、武器、宝石):");
    if (name && name.trim()) {
      const trimmedName = name.trim();
      if (categories.includes(trimmedName)) {
        alert("该分类已存在");
        return;
      }
      setCategories(prev => [...prev, trimmedName]);
      setSelectedCategories(prev => new Set(prev).add(trimmedName));
      setEditingCategory(trimmedName);
      setCatPrompts(prev => ({ ...prev, [trimmedName]: "" }));
      addLog(`已添加自定义分类: ${trimmedName}`);
    }
  };

  const handleDownloadAll = async () => {
    if (images.length === 0 || isZipping) return;
    setIsZipping(true);
    addLog(`准备打包 ${images.length} 张图片...`);
    try {
      const zip = new JSZip();
      images.forEach((img, index) => {
        const base64Data = img.url.split(',')[1];
        const folder = zip.folder(img.category);
        folder?.file(`${img.category}_${index}.png`, base64Data, { base64: true });
      });
      const content = await zip.generateAsync({ type: 'blob' });
      const link = document.createElement('a');
      link.href = URL.createObjectURL(content);
      link.download = `Batch_Export_${Date.now()}.zip`;
      link.click();
      addLog('资源包已成功下载。');
    } catch (error) {
      addLog('下载失败。');
    } finally {
      setIsZipping(false);
    }
  };

  const startGeneration = useCallback(async () => {
    if (progress.status === 'running') return;
    const targetCategories = categories.filter(c => selectedCategories.has(c));
    if (targetCategories.length === 0) return addLog('请先选择分类。');

    if (selectedModel.provider === 'google' && resolution !== '1K' && (window as any).aistudio) {
      const hasKey = await (window as any).aistudio?.hasSelectedApiKey();
      if (!hasKey) {
        await (window as any).aistudio?.openSelectKey();
        return;
      }
    }

    isStopping.current = false;
    const totalCount = targetCategories.length * countPerCategory;
    setProgress({ total: totalCount, current: 0, category: null, status: 'running' });
    addLog(`任务启动: ${selectedModel.name} | 总数: ${totalCount}`);

    let count = 0;
    for (const category of targetCategories) {
      if (isStopping.current) break;
      for (let i = 0; i < countPerCategory; i++) {
        if (isStopping.current) break;
        try {
          setProgress(prev => ({ ...prev, category, current: count + 1 }));
          const result = await geminiService.generateImage(
            category, catPrompts[category] || "", commonSubject,
            globalStyle, negativePrompt, aspectRatio, resolution, selectedModel
          );
          if (result) {
            setImages(prev => [{
              id: crypto.randomUUID(), url: result.url, category, prompt: result.prompt, timestamp: Date.now()
            }, ...prev]);
            addLog(`已完成: ${category} (${i + 1}/${countPerCategory})`);
          }
          count++;
        } catch (e) {
          addLog(`错误: ${category} 生成失败`);
        }
      }
    }
    setProgress(prev => ({ ...prev, status: 'idle', category: null }));
    addLog('所有任务已完成。');
  }, [categories, selectedCategories, commonSubject, globalStyle, negativePrompt, countPerCategory, catPrompts, aspectRatio, resolution, selectedModel, progress.status]);

  return (
    <div className="min-h-screen flex flex-col bg-[#08090a] text-[#e3e4e6] font-sans">
      <nav className="h-16 bg-[#141518] border-b border-[#2e3035] flex items-center px-6 justify-between shrink-0 z-50 shadow-xl">
        <div className="flex items-center gap-4">
          <div className="w-8 h-8 bg-gradient-to-br from-blue-600 to-indigo-600 rounded flex items-center justify-center font-black text-white">G</div>
          <div>
            <h1 className="text-xs font-bold uppercase tracking-widest text-white">Gemini Production</h1>
            <p className="text-[8px] text-zinc-500 font-mono">MULTI-PROVIDER ENGINE V3.2</p>
          </div>
        </div>
        <button onClick={handleDownloadAll} disabled={images.length === 0} className={`px-5 py-2 rounded-lg text-[11px] font-black uppercase border ${images.length === 0 ? 'border-zinc-800 text-zinc-700' : 'bg-red-600 text-white border-red-500'}`}>
          打包下载 ({images.length})
        </button>
      </nav>

      <div className="flex-1 flex overflow-hidden">
        <aside className="w-[420px] bg-[#141518] border-r border-[#2e3035] flex flex-col shrink-0 z-40">
          <div className="p-6 space-y-6 overflow-y-auto custom-scrollbar flex-1">
            <div className="space-y-4">
              <div className="relative group">
                <label className="text-[10px] font-bold text-zinc-500 uppercase tracking-widest block mb-2">通用基础主体</label>
                <div className="relative">
                  <textarea value={commonSubject} onChange={(e) => setCommonSubject(e.target.value)} className="w-full bg-black border border-zinc-800 rounded-lg p-3 pr-10 text-xs min-h-[80px] focus:border-blue-500 outline-none transition-all resize-none shadow-inner" />
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
                  <select value={aspectRatio} onChange={(e) => setAspectRatio(e.target.value as AspectRatio)} className="w-full bg-zinc-900 border border-zinc-800 rounded px-2 py-1.5 text-[10px] outline-none">
                    <option value="16:9">16:9 (Cinematic)</option>
                    <option value="9:16">9:16 (Vertical)</option>
                    <option value="1:1">1:1 (Square)</option>
                  </select>
                </div>
                <div className="space-y-2">
                  <label className="text-[9px] font-bold text-zinc-600 uppercase">画质 (Google)</label>
                  <select value={resolution} onChange={(e) => setResolution(e.target.value as Resolution)} className="w-full bg-zinc-900 border border-zinc-800 rounded px-2 py-1.5 text-[10px] outline-none">
                    <option value="1K">1K 标准</option>
                    <option value="2K">2K 高清</option>
                  </select>
                </div>
              </div>
            </div>

            <div className="space-y-3">
              <label className="text-[10px] font-bold text-zinc-500 uppercase tracking-widest block">生产分类</label>
              <div className="flex flex-wrap gap-1.5">
                {categories.map(cat => (
                  <button key={cat} onClick={() => handleCategoryClick(cat)} className={`px-3 py-1.5 text-[11px] font-bold rounded border transition-all ${selectedCategories.has(cat) ? 'bg-blue-600 text-white border-blue-400' : 'bg-zinc-800 text-zinc-500 border-transparent hover:bg-zinc-700'}`}>
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
                  value={catPrompts[editingCategory] || ""} 
                  onChange={(e) => setCatPrompts({...catPrompts, [editingCategory]: e.target.value})} 
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
                  <input type="number" value={countPerCategory} onChange={(e) => setCountPerCategory(parseInt(e.target.value) || 1)} className="w-full bg-black border border-zinc-800 rounded p-2 text-xs outline-none" />
                </div>
                <div className="text-right text-[10px] font-black text-blue-400 uppercase">预计生成: {selectedCategories.size * countPerCategory} 张</div>
              </div>

              <div className="space-y-3">
                <button 
                  onClick={startGeneration} 
                  disabled={progress.status === 'running' || selectedCategories.size === 0}
                  className={`w-full py-4 rounded-xl text-xs font-black uppercase tracking-widest transition-all ${
                    progress.status === 'running' ? 'bg-zinc-900 text-zinc-700' : 'bg-blue-600 text-white hover:bg-blue-500 shadow-lg shadow-blue-900/20'
                  }`}
                >
                  {progress.status === 'running' ? '正在执行任务流...' : `启动批量生产 (已选 ${selectedCategories.size})`}
                </button>

                <div className="space-y-2">
                  <label className="text-[9px] font-black text-zinc-500 uppercase tracking-tighter block text-center">AI 模型选择 (Model Selection)</label>
                  <div className="relative group">
                    <select 
                      value={selectedModel.id} 
                      onChange={(e) => setSelectedModel(MODELS.find(m => m.id === e.target.value) || MODELS[0])}
                      className="w-full appearance-none bg-[#1a1c20] border border-zinc-800 group-hover:border-blue-500/50 rounded-lg px-4 py-3 text-[11px] font-mono font-bold text-zinc-300 outline-none transition-all cursor-pointer shadow-xl"
                    >
                      {MODELS.map(m => (
                        <option key={m.id} value={m.id}>[{m.provider.toUpperCase()}] {m.name}</option>
                      ))}
                    </select>
                    <div className="absolute inset-y-0 right-3 flex items-center pointer-events-none text-zinc-600 group-hover:text-blue-400">
                      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2.5" d="M19 9l-7 7-7-7"></path></svg>
                    </div>
                  </div>
                  <p className="text-[9px] text-zinc-600 text-center font-medium italic">{selectedModel.description}</p>
                </div>

                {progress.status === 'running' && (
                  <button onClick={() => isStopping.current = true} className="w-full py-2 text-[10px] font-bold text-red-500 uppercase hover:text-red-400 transition-colors">
                    紧急停止作业
                  </button>
                )}
              </div>
            </div>
          </div>
          <div className="h-32 border-t border-zinc-800 bg-black/40 p-4 font-mono text-[9px] overflow-y-auto custom-scrollbar text-zinc-500">
            {logs.map((log, i) => <div key={i} className="mb-1">{log}</div>)}
          </div>
        </aside>

        <main className="flex-1 overflow-y-auto bg-[#08090a] p-10 custom-scrollbar">
          {images.length === 0 ? (
            <div className="h-full flex flex-col items-center justify-center opacity-20">
               <p className="text-xs font-black uppercase tracking-[1em]">Ready for Production</p>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
              {images.map(img => <ImageCard key={img.id} image={img} />)}
            </div>
          )}
        </main>
      </div>
    </div>
  );
};

export default App;

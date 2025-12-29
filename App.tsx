
import React, { useState, useCallback, useRef, useEffect, useMemo } from 'react';
import { Category, GeneratedImage, BatchProgress, AspectRatio, Resolution, ModelInfo } from './types';
import { geminiService } from './services/geminiService';
import { ImageCard } from './components/ImageCard';
import JSZip from 'jszip';

const MODELS: ModelInfo[] = [
  {
    id: 'wan',
    name: 'Aliyun Wan 2.6',
    provider: 'aliyun',
    modelName: 'wan2.6-t2i',
    description: '通义万相 2.6 - 文本生成图像'
  },
  {
    id: 'z_image',
    name: 'Z-Image Turbo',
    provider: 'z_image',
    modelName: 'z-image-turbo',
    description: 'Z-Image Turbo - 高速图像生成'
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
  // Removed hardcoded "Style: ..." prefix in backend, managed by frontend prompt assembly
  // but wait, geminiService.ts handles prompt assembly.
  // Let's check geminiService.ts next. 
  const [negativePrompt, setNegativePrompt] = useState('文字，水印，签名，模糊，重影，低对比度，畸形肢体');
  const [countPerCategory, setCountPerCategory] = useState<number>(4);

  // Load default prompts from backend on mount
  useEffect(() => {
    fetch('/api/config/prompts')
      .then(res => res.json())
      .then(data => {
        if (data.default_style) setGlobalStyle(data.default_style);
        if (data.default_negative_prompt) setNegativePrompt(data.default_negative_prompt);
      })
      .catch(console.error);
  }, []);
  const [aspectRatio, setAspectRatio] = useState<AspectRatio>('16:9');
  const [resolution, setResolution] = useState<Resolution>('1080p');
  
  const [selectedModel, setSelectedModel] = useState<ModelInfo>(MODELS[0]);
  const [categories, setCategories] = useState<string[]>(INITIAL_CATEGORIES);
  const [selectedCategory, setSelectedCategory] = useState<string>(Category.ENVIRONMENT);
  const [editingCategory, setEditingCategory] = useState<string>(Category.ENVIRONMENT);
  const [catPrompts, setCatPrompts] = useState<Record<string, string>>(INITIAL_PROMPTS);
  const getMaxPerModel = (m: ModelInfo) => {
    if (!m) return 4;
    if (m.id === 'wan' || m.provider === 'aliyun') return 2;
    return 4;
  };
  const currentMax = useMemo(() => getMaxPerModel(selectedModel), [selectedModel]);
  
  const [images, setImages] = useState<GeneratedImage[]>([]);
  const [currentPage, setCurrentPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);
  const [selectedImages, setSelectedImages] = useState<Set<string>>(new Set());
  const [lastSelectedId, setLastSelectedId] = useState<string | null>(null);

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

  const fetchImages = useCallback(async (page = 1) => {
    try {
      const offset = (page - 1) * pageSize;
      const resp = await fetch(`/api/images?limit=${pageSize}&offset=${offset}`);
      const data = await resp.json();
      const list = (data?.images || []) as Array<any>;
      
      const loaded = list.map((it) => ({
        id: String(it.id || crypto.randomUUID()),
        url: String(it.thumbUrl || it.url || it.originalUrl || ''),
        originalUrl: it.originalUrl ? String(it.originalUrl) : undefined,
        category: String(it.category || 'default'),
        prompt: String(it.prompt || it.filename || ''),
        timestamp: Number(it.timestamp || Date.now()),
        filename: it.filename ? String(it.filename) : undefined,
      })) as GeneratedImage[];
      
      setImages(loaded);
      setCurrentPage(page);
    } catch (e) {
      console.error("Failed to fetch images", e);
    }
  }, [pageSize]);

  useEffect(() => {
    let canceled = false;
    fetchImages(1);
    return () => { canceled = true; };
  }, [fetchImages]);
  useEffect(() => {
    setCountPerCategory(c => Math.max(1, Math.min(c, currentMax)));
  }, [currentMax]);

  const handleImageClick = (img: GeneratedImage) => {
      // Open raw image in new tab
      window.open(img.originalUrl || img.url, '_blank');
  };

  const toggleSelection = (e: React.MouseEvent, id: string) => {
    e.stopPropagation();
    const newSelected = new Set(selectedImages);
    
    if (e.shiftKey && lastSelectedId && newSelected.has(lastSelectedId)) {
       // Range selection
       const currentIndex = images.findIndex(img => img.id === id);
       const lastIndex = images.findIndex(img => img.id === lastSelectedId);
       
       if (currentIndex !== -1 && lastIndex !== -1) {
          const start = Math.min(currentIndex, lastIndex);
          const end = Math.max(currentIndex, lastIndex);
          const range = images.slice(start, end + 1);
          range.forEach(img => newSelected.add(img.id));
       } else {
          newSelected.add(id);
       }
    } else {
       if (newSelected.has(id)) {
         newSelected.delete(id);
       } else {
         newSelected.add(id);
       }
    }
    
    setSelectedImages(newSelected);
    setLastSelectedId(id);
  };

  const handleDownload = async () => {
    if (selectedImages.size === 0) return;
    setIsZipping(true);
    try {
       // Filter images from current view
       const targets = images.filter(img => selectedImages.has(img.id)).map(img => img.filename).filter(Boolean);
       
       if (targets.length === 0) {
           alert("未找到选中图片的文件信息 (可能已翻页?)");
           setIsZipping(false);
           return;
       }

       const resp = await fetch('/api/download', {
          method: 'POST',
          headers: {'Content-Type': 'application/json'},
          body: JSON.stringify({ filenames: targets })
       });
       
       if (!resp.ok) {
          const err = await resp.json();
          if (resp.status === 404) {
             alert(`部分文件缺失: ${err.missing_files?.join(', ')}`);
          } else {
             alert(`打包失败: ${err.detail?.error || '未知错误'}`);
          }
          return;
       }
       
       const data = await resp.json();
       if (data.status === 'success' && data.url) {
          const link = document.createElement('a');
          link.href = data.url;
          link.download = `images_打包_${Date.now()}.zip`;
          document.body.appendChild(link);
          link.click();
          document.body.removeChild(link);
          addLog(`下载已启动: ${data.size}`);
       }
    } catch (e) {
       console.error(e);
       addLog("下载请求失败");
    } finally {
       setIsZipping(false);
    }
  };
  const handleCategoryClick = (cat: string) => {
    setEditingCategory(cat);
    setSelectedCategory(cat);
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
      setSelectedCategory(trimmedName);
      setEditingCategory(trimmedName);
      setCatPrompts(prev => ({ ...prev, [trimmedName]: "" }));
      addLog(`已添加自定义分类: ${trimmedName}`);
    }
  };

  const startGeneration = useCallback(async () => {
    if (progress.status === 'running') return;
    const targetCategory = selectedCategory;
    if (!targetCategory) return addLog('请先选择分类。');

    // if (selectedModel.provider === 'google' && resolution !== '1K') {
    //   const hasKey = await (window as any).aistudio?.hasSelectedApiKey();
    //   if (!hasKey) {
    //     await (window as any).aistudio?.openSelectKey();
    //     return;
    //   }
    // }

    isStopping.current = false;
    const cappedCount = Math.max(1, Math.min(countPerCategory, currentMax));
    const totalCount = cappedCount;
    setProgress({ total: totalCount, current: 0, category: targetCategory, status: 'running' });
    addLog(`任务启动: ${selectedModel.name} | 分类: ${targetCategory} | 总数: ${totalCount} (上限${currentMax})`);

    try {
      const result = await geminiService.generateImage(
        targetCategory, catPrompts[targetCategory] || "", commonSubject,
        globalStyle, negativePrompt, aspectRatio, resolution, selectedModel, cappedCount
      );
      const urlsLen = Array.isArray(result?.urls) ? result!.urls.length : 0;
      if (result) {
        addLog(`已完成: ${targetCategory} (${urlsLen}/${cappedCount})`);
        await fetchImages(1);
      }
      setProgress(prev => ({ ...prev, current: Math.min(urlsLen || cappedCount, totalCount), status: 'idle', category: null }));
      addLog('所有任务已完成。');
    } catch (e) {
      addLog(`错误: ${targetCategory} 生成失败`);
      setProgress(prev => ({ ...prev, status: 'idle', category: null }));
    }
  }, [categories, selectedCategory, commonSubject, globalStyle, negativePrompt, countPerCategory, catPrompts, aspectRatio, resolution, selectedModel, progress.status, fetchImages, currentMax]);

  const handleSelectAll = () => {
     if (selectedImages.size === images.length) {
         setSelectedImages(new Set());
     } else {
         setSelectedImages(new Set(images.map(i => i.id)));
     }
  };

  return (
    <div className="flex flex-col h-screen text-gray-100 font-sans selection:bg-blue-500/30">
      {/* Header */}
      <header className="flex items-center justify-between px-6 py-4 bg-[#08090a] border-b border-gray-800">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 bg-blue-600 rounded-lg flex items-center justify-center font-bold text-lg">G</div>
          <div>
            <h1 className="text-sm font-bold tracking-wider">GEMINI PRODUCTION</h1>
            <p className="text-[10px] text-gray-500 tracking-widest">MULTI-PROVIDER ENGINE V3.2</p>
          </div>
        </div>
        <div className="flex items-center gap-4">
           {selectedImages.size > 0 && (
              <span className="text-sm text-gray-400">已选 {selectedImages.size} 张</span>
           )}
           <button
            onClick={handleDownload}
            disabled={selectedImages.size === 0 || isZipping}
            className={`px-4 py-2 rounded text-sm font-medium transition-all ${
               selectedImages.size > 0 
               ? 'bg-gradient-to-r from-red-600 to-red-500 hover:from-red-500 hover:to-red-400 text-white shadow-lg shadow-red-900/20' 
               : 'bg-gray-800 text-gray-500 cursor-not-allowed opacity-50'
            }`}
          >
            {isZipping ? (
               <span className="flex items-center gap-2">
                 <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none"></circle>
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                 </svg>
                 打包中...
               </span>
            ) : `打包下载 (${selectedImages.size})`}
          </button>
        </div>
      </header>

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
                  <select value={resolution} onChange={(e) => setResolution(e.target.value as Resolution)} className="w-full bg-zinc-900 border border-zinc-800 rounded px-2 py-1.5 text-[10px] outline-none">
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
                  <button key={cat} onClick={() => handleCategoryClick(cat)} className={`px-3 py-1.5 text-[11px] font-bold rounded border transition-all ${selectedCategory === cat ? 'bg-blue-600 text-white border-blue-400' : 'bg-zinc-800 text-zinc-500 border-transparent hover:bg-zinc-700'}`}>
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
                  <label className="text-[10px] font-bold text-zinc-500 uppercase tracking-widest block mb-2">每类数量 (上限{currentMax})</label>
                  <input type="number" min={1} max={currentMax} value={countPerCategory} onChange={(e) => {
                    const v = parseInt(e.target.value) || 1;
                    setCountPerCategory(Math.max(1, Math.min(v, currentMax)));
                  }} className="w-full bg-black border border-zinc-800 rounded p-2 text-xs outline-none" />
                </div>
                <div className="text-right text-[10px] font-black text-blue-400 uppercase">预计生成: {Math.max(1, Math.min(countPerCategory, currentMax))} 张</div>
              </div>

              <div className="space-y-3">
                <button 
                  onClick={startGeneration} 
                  disabled={progress.status === 'running' || !selectedCategory}
                  className={`w-full py-4 rounded-xl text-xs font-black uppercase tracking-widest transition-all ${
                    progress.status === 'running' ? 'bg-zinc-900 text-zinc-700' : 'bg-blue-600 text-white hover:bg-blue-500 shadow-lg shadow-blue-900/20'
                  }`}
                >
                  {progress.status === 'running' ? '正在执行任务流...' : `启动批量生产 (已选 ${selectedCategory})`}
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
                    紧急停止作业（单选，最大{currentMax}张）
                  </button>
                )}
              </div>
            </div>
          </div>
          <div className="h-32 border-t border-zinc-800 bg-black/40 p-4 font-mono text-[9px] overflow-y-auto custom-scrollbar text-zinc-500">
            {logs.map((log, i) => <div key={i} className="mb-1">{log}</div>)}
          </div>
        </aside>

        <div className="flex-1 bg-black border border-gray-800 rounded-lg p-4 overflow-hidden flex flex-col m-6">
          <div className="flex-1 overflow-y-auto min-h-0 grid grid-cols-4 gap-4 content-start pr-2">
            {images.map((img) => (
              <div 
                key={img.id} 
                className={`relative group aspect-video bg-gray-900 rounded-lg overflow-hidden border transition-all cursor-pointer ${
                   selectedImages.has(img.id) ? 'border-blue-500 ring-1 ring-blue-500' : 'border-gray-800 hover:border-gray-600'
                }`}
                onClick={() => handleImageClick(img)}
              >
                <img 
                  src={img.url} 
                  alt={img.prompt}
                  className="w-full h-full object-cover"
                  loading="lazy"
                />
                
                {/* Checkbox Overlay */}
                <div 
                   className="absolute top-2 right-2 w-6 h-6 z-10"
                   onClick={(e) => toggleSelection(e, img.id)}
                >
                   <div className={`w-full h-full rounded border flex items-center justify-center transition-colors ${
                      selectedImages.has(img.id) 
                      ? 'bg-blue-600 border-blue-500' 
                      : 'bg-black/40 border-gray-400 hover:border-white'
                   }`}>
                      {selectedImages.has(img.id) && (
                         <svg className="w-4 h-4 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M5 13l4 4L19 7" />
                         </svg>
                      )}
                   </div>
                </div>

                <div className="absolute inset-0 bg-black/60 opacity-0 group-hover:opacity-100 transition-opacity flex flex-col justify-end p-2 pointer-events-none">
                  <p className="text-xs text-gray-300 line-clamp-2 mb-1">{img.prompt}</p>
                  <div className="flex justify-between items-center text-[10px] text-gray-500">
                    <span>{new Date(img.timestamp).toLocaleTimeString()}</span>
                    <span className="bg-gray-800 px-1 rounded">{img.category}</span>
                  </div>
                </div>
              </div>
            ))}
            {/* Fill remaining slots to keep grid stable if < 20 */}
            {Array.from({ length: Math.max(0, pageSize - images.length) }).map((_, i) => (
               <div key={`empty-${i}`} className="aspect-video bg-gray-900/50 rounded-lg border border-gray-800/50 border-dashed" />
            ))}
          </div>
          
          {/* Pagination Controls */}
          <div className="h-12 border-t border-gray-800 flex items-center justify-between px-2 mt-2 bg-[#08090a]">
             <button 
               onClick={() => fetchImages(Math.max(1, currentPage - 1))}
               disabled={currentPage === 1}
               className="px-3 py-1 bg-gray-800 hover:bg-gray-700 disabled:opacity-50 disabled:cursor-not-allowed rounded text-sm text-gray-300 transition-colors"
             >
               上一页
             </button>
             <span className="text-gray-400 text-sm">第 {currentPage} 页</span>
             <button 
               onClick={() => fetchImages(currentPage + 1)}
               disabled={images.length < pageSize} // Simple check for next page availability
               className="px-3 py-1 bg-gray-800 hover:bg-gray-700 disabled:opacity-50 disabled:cursor-not-allowed rounded text-sm text-gray-300 transition-colors"
             >
               下一页
             </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default App;

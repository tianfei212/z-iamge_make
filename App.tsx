
import React, { useState, useCallback, useRef, useEffect } from 'react';
import { Category, GeneratedImage, BatchProgress, AspectRatio, Resolution, ModelInfo } from './types';
import { geminiService } from './services/geminiService';
import JSZip from 'jszip';
import { SettingsPage } from './pages/SettingsPage';
import { GalleryPage } from './pages/GalleryPage';
import { LogsPanel } from './pages/LogsPanel';
import { IconButton } from './components/IconButton';
import { Modal } from './components/Modal';
import { t } from './i18n';
import { ConfigManagement } from './pages/ConfigManagement';
import { ImageDetailModal } from './components/ImageDetailModal';

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
  const [countPerCategory, setCountPerCategory] = useState<number>(20);

  // Model selection and limits
  const [selectedModel, setSelectedModel] = useState<ModelInfo>(MODELS[0]);
  const [modelLimits, setModelLimits] = useState<Record<string, number>>({});
  const currentLimit = modelLimits[selectedModel.modelName] ?? (selectedModel.provider === 'z_image' ? 4 : 2);
  useEffect(() => {
    setCountPerCategory(prev => Math.max(1, Math.min(prev, currentLimit)));
  }, [selectedModel, currentLimit]);
  useEffect(() => {
    (async () => {
      try {
        await fetch('/api/config/reload', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ reason: 'page_load' }) });
        const r1 = await fetch('/api/config/runtime').then(r => r.json());
        if (r1?.global) {
          if (typeof r1.global.global_style === 'string') setGlobalStyle(r1.global.global_style);
          if (typeof r1.global.negative_prompt === 'string') setNegativePrompt(r1.global.negative_prompt);
          if (typeof r1.global.common_subject === 'string' && r1.global.common_subject) setCommonSubject(r1.global.common_subject);
        }
        if (Array.isArray(r1?.categories) && r1.categories.length > 0) {
          setCategories(r1.categories);
          const def = r1.categories.includes('环境') ? '环境' : r1.categories[0];
          setSelectedCategories(new Set([def]));
          setEditingCategory(def);
        } else {
          // fallback: keep INITIAL_CATEGORIES, default to 环境
          const def = INITIAL_CATEGORIES.includes('环境') ? '环境' : INITIAL_CATEGORIES[0];
          setSelectedCategories(new Set([def]));
          setEditingCategory(def);
        }
        if (r1?.prompts && typeof r1.prompts === 'object') {
          setCatPrompts(r1.prompts);
        }
      } catch (e) {
        console.error(e);
        // fallback defaults already set
      }
      try {
        const r2 = await fetch('/api/config/limits').then(r => r.json());
        if (r2?.model_limits && typeof r2.model_limits === 'object') {
          setModelLimits(r2.model_limits);
        }
      } catch (e) {
        console.error(e);
      }
    })();
  }, []);
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'F5' || e.keyCode === 116) {
        try {
          fetch('/api/config/reload', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ reason: 'key_f5' }), keepalive: true }).catch(() => {});
        } catch {}
      }
    };
    const onUnload = () => {
      try {
        const data = new Blob([JSON.stringify({ reason: 'before_unload' })], { type: 'application/json' });
        navigator.sendBeacon('/api/config/reload', data);
      } catch {}
    };
    window.addEventListener('keydown', onKey);
    window.addEventListener('beforeunload', onUnload);
    return () => {
      window.removeEventListener('keydown', onKey);
      window.removeEventListener('beforeunload', onUnload);
    };
  }, []);
  const [aspectRatio, setAspectRatio] = useState<AspectRatio>('16:9');
  const [resolution, setResolution] = useState<Resolution>('1080p');
  const [categories, setCategories] = useState<string[]>(INITIAL_CATEGORIES);
  const [selectedCategories, setSelectedCategories] = useState<Set<string>>(new Set(['环境']));
  const [editingCategory, setEditingCategory] = useState<string>('环境');
  const [catPrompts, setCatPrompts] = useState<Record<string, string>>(INITIAL_PROMPTS);
  
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

  const [openDetail, setOpenDetail] = useState(false);
  const [detailTarget, setDetailTarget] = useState<{ filename: string; category?: string; thumbUrl?: string } | null>(null);
  const handleImageClick = (img: GeneratedImage) => {
      setDetailTarget({ filename: img.filename || '', category: img.category, thumbUrl: img.url });
      setOpenDetail(true);
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
    setSelectedCategories(new Set([cat]));
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
      setSelectedCategories(new Set([trimmedName]));
      setEditingCategory(trimmedName);
      setCatPrompts(prev => ({ ...prev, [trimmedName]: "" }));
      addLog(`已添加自定义分类: ${trimmedName}`);
    }
  };

  const startGeneration = useCallback(async () => {
    if (progress.status === 'running') return;
    const targetCategories = categories.filter(c => selectedCategories.has(c)).slice(0, 1);
    if (targetCategories.length === 0) return addLog('请先选择分类。');

    // if (selectedModel.provider === 'google' && resolution !== '1K') {
    //   const hasKey = await (window as any).aistudio?.hasSelectedApiKey();
    //   if (!hasKey) {
    //     await (window as any).aistudio?.openSelectKey();
    //     return;
    //   }
    // }

    isStopping.current = false;
    const totalCount = targetCategories.length * Math.min(countPerCategory, currentLimit);
    setProgress({ total: totalCount, current: 0, category: null, status: 'running' });
    addLog(`任务启动: ${selectedModel.name} | 总数: ${totalCount}`);

    let count = 0;
    for (const category of targetCategories) {
      if (isStopping.current) break;
      for (let i = 0; i < Math.min(countPerCategory, currentLimit); i++) {
        if (isStopping.current) break;
        try {
          setProgress(prev => ({ ...prev, category, current: count + 1 }));
          const result = await geminiService.generateImage(
            category, catPrompts[category] || "", commonSubject,
            globalStyle, negativePrompt, aspectRatio, resolution, selectedModel
          );
          if (result) {
            // After successful generation, force refresh page 1 to show new images
            // This ensures we see the latest thumbnails immediately
            addLog(`已完成: ${category} (${i + 1}/${countPerCategory})`);
            await fetchImages(1);
          }
          count++;
        } catch (e) {
          addLog(`错误: ${category} 生成失败`);
        }
      }
    }
    setProgress(prev => ({ ...prev, status: 'idle', category: null }));
    addLog('所有任务已完成。');
  }, [categories, selectedCategories, commonSubject, globalStyle, negativePrompt, countPerCategory, catPrompts, aspectRatio, resolution, selectedModel, progress.status, fetchImages]);

  const handleSelectAll = () => {
     if (selectedImages.size === images.length) {
         setSelectedImages(new Set());
     } else {
         setSelectedImages(new Set(images.map(i => i.id)));
     }
  };

  const [openFeatureModal, setOpenFeatureModal] = useState(false);

  return (
    <div className="flex flex-col h-screen text-gray-100 font-sans selection:bg-blue-500/30">
      {/* Header */}
      <header className="flex items-center justify-between px-6 py-4 bg-[#08090a] border-b border-gray-800">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 bg-blue-600 rounded-lg flex items-center justify-center font-bold text-lg">G</div>
          <div>
            <h1 className="text-sm font-bold tracking-wider">{t('app.title')}</h1>
            <p className="text-[10px] text-gray-500 tracking-widest">{t('app.subtitle')}</p>
          </div>
        </div>
        <div className="flex items-center gap-4">
           <IconButton title="功能" onClick={() => setOpenFeatureModal(true)} />
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
            <SettingsPage
              commonSubject={commonSubject}
              setCommonSubject={setCommonSubject}
              aspectRatio={aspectRatio}
              setAspectRatio={setAspectRatio}
              resolution={resolution}
              setResolution={setResolution}
              categories={categories}
              selectedCategories={selectedCategories}
              editingCategory={editingCategory}
              setEditingCategory={setEditingCategory}
              catPrompts={catPrompts}
              setCatPrompts={(next) => setCatPrompts(next)}
              handleCategoryClick={handleCategoryClick}
              handleAddCustomCategory={handleAddCustomCategory}
              handleTranslate={handleTranslate}
              isTranslating={isTranslating}
              countPerCategory={countPerCategory}
              setCountPerCategory={(n) => setCountPerCategory(Math.max(1, Math.min(n, currentLimit)))}
              modelLimit={currentLimit}
              startGeneration={() => startGeneration()}
              progressStatus={progress.status}
              selectedModel={selectedModel}
              setSelectedModel={setSelectedModel}
              models={MODELS}
              stopNow={() => { isStopping.current = true; }}
            />
          </div>
          <LogsPanel logs={logs} />
        </aside>

        <GalleryPage
          images={images}
          pageSize={pageSize}
          currentPage={currentPage}
          fetchImages={(p) => fetchImages(p)}
          selectedImages={selectedImages}
          toggleSelection={toggleSelection}
          handleImageClick={handleImageClick}
        />
      </div>

      {detailTarget ? (
        <ImageDetailModal
          open={openDetail}
          onClose={() => setOpenDetail(false)}
          filename={detailTarget.filename}
          category={detailTarget.category}
          thumbUrl={detailTarget.thumbUrl}
        />
      ) : null}

      <Modal
        open={openFeatureModal}
        onClose={() => setOpenFeatureModal(false)}
        title={undefined}
      >
        <ConfigManagement />
      </Modal>
    </div>
  );
};

export default App;

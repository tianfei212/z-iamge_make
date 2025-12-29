import React, { useEffect, useRef, useState } from 'react';
import { Modal } from './Modal';
import { getImageDetails, ImageDetails } from '../services/imageService';
import { showToast } from './Toast';
import { geminiService } from '../services/geminiService';

interface ImageDetailModalProps {
  open: boolean;
  onClose: () => void;
  filename: string;
  category?: string;
  thumbUrl?: string;
}

export const ImageDetailModal: React.FC<ImageDetailModalProps> = ({ open, onClose, filename, category, thumbUrl }) => {
  const [loading, setLoading] = useState(false);
  const [details, setDetails] = useState<ImageDetails | null>(null);
  const [error, setError] = useState<string | null>(null);
  const containerRef = useRef<HTMLDivElement | null>(null);
  const [scale, setScale] = useState(1);
  const [tx, setTx] = useState(0);
  const [ty, setTy] = useState(0);
  const [dragging, setDragging] = useState(false);
  const dragStart = useRef<{ x: number; y: number; tx: number; ty: number } | null>(null);
  const [translatingPos, setTranslatingPos] = useState(false);
  const [translatingNeg, setTranslatingNeg] = useState(false);

  useEffect(() => {
    if (!open) return;
    let canceled = false;
    const run = async () => {
      setLoading(true);
      setError(null);
      try {
        const d = await getImageDetails({ filename, category });
        if (canceled) return;
        setDetails(d);
        setScale(1);
        setTx(0);
        setTy(0);
      } catch (e: any) {
        const msg = String(e?.message || '加载失败');
        setError(msg);
        showToast(msg, 'error');
      } finally {
        setLoading(false);
      }
    };
    run();
    return () => {
      canceled = true;
    };
  }, [open, filename, category]);

  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;
    const onWheel = (e: WheelEvent) => {
      e.preventDefault();
      const delta = Math.sign(e.deltaY) * 0.1;
      setScale(s => Math.max(0.5, Math.min(4, s - delta)));
    };
    el.addEventListener('wheel', onWheel, { passive: false });
    return () => el.removeEventListener('wheel', onWheel);
  }, []);

  const onMouseDown = (e: React.MouseEvent) => {
    setDragging(true);
    dragStart.current = { x: e.clientX, y: e.clientY, tx, ty };
  };
  const onMouseMove = (e: React.MouseEvent) => {
    if (!dragging || !dragStart.current) return;
    const dx = e.clientX - dragStart.current.x;
    const dy = e.clientY - dragStart.current.y;
    setTx(dragStart.current.tx + dx);
    setTy(dragStart.current.ty + dy);
  };
  const onMouseUp = () => {
    setDragging(false);
    dragStart.current = null;
  };
  const onDoubleClick = () => {
    setScale(1);
    setTx(0);
    setTy(0);
  };

  const openRawInNewTab = () => {
    const url = details?.image?.originalUrl || details?.image?.url || thumbUrl;
    if (url) window.open(url, '_blank');
  };
  const copyText = (text: string | null | undefined) => {
    if (!text) return;
    navigator.clipboard.writeText(text).then(() => showToast('已复制', 'success')).catch(() => showToast('复制失败', 'error'));
  };
  const translatePositive = async () => {
    const src = details?.prompts?.positive;
    if (!src) return;
    setTranslatingPos(true);
    try {
      const out = await geminiService.translateText(src);
      setDetails(prev => prev ? { ...prev, prompts: { ...prev.prompts, positive: out } } : prev);
      showToast('已翻译正向提示词', 'success');
    } catch {
      showToast('正向提示词翻译失败', 'error');
    } finally {
      setTranslatingPos(false);
    }
  };
  const translateNegative = async () => {
    const src = details?.prompts?.negative;
    if (!src) return;
    setTranslatingNeg(true);
    try {
      const out = await geminiService.translateText(src);
      setDetails(prev => prev ? { ...prev, prompts: { ...prev.prompts, negative: out } } : prev);
      showToast('已翻译反向提示词', 'success');
    } catch {
      showToast('反向提示词翻译失败', 'error');
    } finally {
      setTranslatingNeg(false);
    }
  };

  return (
    <Modal open={open} onClose={onClose} title={undefined}>
      <div className="h-full w-full flex flex-col sm:flex-row gap-4">
        <div className="sm:basis-1/3 basis-full min-h-0 overflow-auto border border-[#2e3035] rounded p-3">
          {loading ? (
            <div className="h-full w-full flex items-center justify-center">
              <svg className="animate-spin h-5 w-5 text-zinc-300" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none"></circle>
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
              </svg>
            </div>
          ) : error ? (
            <div className="space-y-2">
              <p className="text-sm text-red-500">加载失败：{error}</p>
              <button
                className="px-3 py-1 text-sm rounded bg-zinc-800 hover:bg-zinc-700"
                onClick={() => {
                  setDetails(null);
                  setLoading(true);
                  setError(null);
                  getImageDetails({ filename, category })
                    .then(d => setDetails(d))
                    .catch(e => setError(String(e?.message || '加载失败')))
                    .finally(() => setLoading(false));
                }}
              >
                重试
              </button>
            </div>
          ) : (
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <div>
                  <div className="text-xs text-zinc-400">{details?.image?.category}</div>
                  <div className="text-sm font-semibold">{details?.image?.filename}</div>
                </div>
                <div className="flex gap-2">
                  <button className="px-2 py-1 text-xs rounded bg-zinc-800 hover:bg-zinc-700" onClick={openRawInNewTab}>
                    打开原图
                  </button>
                </div>
              </div>
              <div>
                <h3 className="text-xs font-bold text-blue-400 mb-1">正向提示词</h3>
                <p className="text-sm whitespace-pre-wrap break-words">{details?.prompts?.positive || '（无）'}</p>
                <div className="mt-2 flex gap-2">
                  <button className="px-2 py-1 text-xs rounded bg-white/10 hover:bg-white/20" onClick={() => copyText(details?.prompts?.positive)}>
                    复制正向提示词
                  </button>
                  <button
                    disabled={translatingPos || !details?.prompts?.positive}
                    className={`px-2 py-1 text-xs rounded ${translatingPos ? 'bg-zinc-700' : 'bg-white/10 hover:bg-white/20'}`}
                    onClick={translatePositive}
                  >
                    {translatingPos ? '翻译中...' : '翻译正向提示词'}
                  </button>
                </div>
              </div>
              <div>
                <h3 className="text-xs font-bold text-red-400 mb-1">反向提示词</h3>
                <p className="text-sm whitespace-pre-wrap break-words">{details?.prompts?.negative || '（无）'}</p>
                <div className="mt-2 flex gap-2">
                  <button className="px-2 py-1 text-xs rounded bg-white/10 hover:bg-white/20" onClick={() => copyText(details?.prompts?.negative)}>
                    复制反向提示词
                  </button>
                  <button
                    disabled={translatingNeg || !details?.prompts?.negative}
                    className={`px-2 py-1 text-xs rounded ${translatingNeg ? 'bg-zinc-700' : 'bg-white/10 hover:bg-white/20'}`}
                    onClick={translateNegative}
                  >
                    {translatingNeg ? '翻译中...' : '翻译反向提示词'}
                  </button>
                </div>
              </div>
            </div>
          )}
        </div>
        <div
          ref={containerRef}
          className="sm:basis-2/3 basis-full min-h-0 overflow-hidden border border-[#2e3035] rounded bg-black relative select-none"
          onMouseDown={onMouseDown}
          onMouseMove={onMouseMove}
          onMouseUp={onMouseUp}
          onMouseLeave={onMouseUp}
          onDoubleClick={onDoubleClick}
        >
          {!details && thumbUrl ? (
            <img src={thumbUrl} alt={filename} className="absolute inset-0 w-full h-full object-contain opacity-40" />
          ) : null}
          {details?.image?.originalUrl ? (
            <img
              src={details.image.originalUrl}
              alt={details.image.filename}
              className="absolute inset-0 w-full h-full object-contain"
              style={{ transform: `translate(${tx}px, ${ty}px) scale(${scale})`, transformOrigin: 'center center' }}
              draggable={false}
            />
          ) : null}
        </div>
      </div>
    </Modal>
  );
};

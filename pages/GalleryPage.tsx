import React from 'react';
import { GeneratedImage } from '../types';

interface GalleryPageProps {
  images: GeneratedImage[];
  pageSize: number;
  currentPage: number;
  fetchImages: (page: number) => void;
  selectedImages: Set<string>;
  toggleSelection: (e: React.MouseEvent, id: string) => void;
  handleImageClick: (img: GeneratedImage) => void;
}

export const GalleryPage: React.FC<GalleryPageProps> = ({
  images,
  pageSize,
  currentPage,
  fetchImages,
  selectedImages,
  toggleSelection,
  handleImageClick
}) => {
  return (
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

            <div
              className="absolute top-2 right-2 w-6 h-6 z-10"
              onClick={(e) => toggleSelection(e, img.id)}
            >
              <div
                className={`w-full h-full rounded border flex items-center justify-center transition-colors ${
                  selectedImages.has(img.id)
                    ? 'bg-blue-600 border-blue-500'
                    : 'bg-black/40 border-gray-400 hover:border-white'
                }`}
              >
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
        {Array.from({ length: Math.max(0, pageSize - images.length) }).map((_, i) => (
          <div key={`empty-${i}`} className="aspect-video bg-gray-900/50 rounded-lg border border-gray-800/50 border-dashed" />
        ))}
      </div>
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
          disabled={images.length < pageSize}
          className="px-3 py-1 bg-gray-800 hover:bg-gray-700 disabled:opacity-50 disabled:cursor-not-allowed rounded text-sm text-gray-300 transition-colors"
        >
          下一页
        </button>
      </div>
    </div>
  );
};


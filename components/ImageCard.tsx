
import React from 'react';
import { GeneratedImage } from '../types';

interface ImageCardProps {
  image: GeneratedImage;
}

export const ImageCard: React.FC<ImageCardProps> = ({ image }) => {
  return (
    <div className="group relative overflow-hidden rounded-xl bg-zinc-900 border border-zinc-800 transition-all hover:border-blue-500/50">
      <div className="aspect-video w-full overflow-hidden bg-zinc-950">
        <img 
          src={image.url} 
          alt={image.category}
          className="h-full w-full object-cover transition-transform duration-500 group-hover:scale-110"
          loading="lazy"
        />
      </div>
      <div className="absolute inset-0 flex flex-col justify-end bg-gradient-to-t from-black/90 via-black/40 to-transparent p-4 opacity-0 transition-opacity group-hover:opacity-100">
        <p className="text-xs font-medium text-blue-400 uppercase tracking-wider mb-1">
          {image.category}
        </p>
        <p className="text-sm text-zinc-200 line-clamp-2">
          {image.prompt}
        </p>
        <button 
          onClick={() => window.open(image.originalUrl || image.url, '_blank')}
          className="mt-3 text-[10px] bg-white/10 hover:bg-white/20 text-white py-1 px-3 rounded-full backdrop-blur-sm self-start transition-colors"
        >
          查看原图
        </button>
      </div>
    </div>
  );
};

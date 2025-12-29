
import { AspectRatio, Resolution, ModelInfo } from "../types";

export class ImageGenerationService {
  constructor() {}

  async translateText(text: string): Promise<string> {
    if (!text || text.trim().length === 0) return text;
    try {
      const resp = await fetch('/api/translate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text })
      });
      const data = await resp.json();
      if (!resp.ok) throw new Error(data?.message || 'Translation failed');
      return (data?.output as string)?.trim() || text;
    } catch (error) {
      console.error("[Translation] Error:", error);
      return text;
    }
  }

  async generateImage(
    category: string, 
    specificPrompt: string, 
    commonSubject: string,
    globalStyle: string,
    negativePrompt: string,
    aspectRatio: AspectRatio,
    resolution: Resolution,
    model: ModelInfo,
    count: number = 1
  ): Promise<{urls: string[], prompt: string} | null> {
    
    // 按照需求：自动将"通用基础主体"内容以逗号分隔符附加到"生产分类"内容之后
    // 格式：[生产分类], [通用基础主体], [特定描述]. [风格] - [参数]
    // 注意：Style 应该由前端拼接，而不是后端硬编码
    const parts = [
      category,
      commonSubject,
      specificPrompt
    ].filter(s => s && s.trim());
    
    let finalPrompt = parts.join(', ');
    
    if (globalStyle && globalStyle.trim()) {
      // 检查是否已经包含了 Style 前缀 (避免重复)
      const styleContent = globalStyle.trim();
      if (!styleContent.toLowerCase().startsWith('style:')) {
          finalPrompt += `. Style: ${styleContent}`;
      } else {
          finalPrompt += `. ${styleContent}`;
      }
    }
    
    // 添加比例和画质到提示词中 (作为参数提示词)
    const params = [];
    if (aspectRatio) params.push(`Aspect Ratio: ${aspectRatio}`);
    if (resolution) params.push(`Resolution: ${resolution}`);
    
    if (params.length > 0) {
      finalPrompt += ` - ${params.join(', ')}`;
    }

    return this.generateWithBackend(finalPrompt, category, negativePrompt, aspectRatio, resolution, model, count);
  }

  private async generateWithBackend(
    prompt: string, 
    category: string,
    negativePrompt: string, 
    aspectRatio: string,
    resolution: Resolution,
    model: ModelInfo,
    count: number
  ) {
    try {
      const size = this.mapAspectRatioToAliyun(aspectRatio);
      const service = this.inferService(model);
      const sessionId = await this.getStableSessionId();
      const userId = this.getUserId();

      const resp = await fetch('/api/generate', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-Session-ID': sessionId,
          'X-User-ID': userId,
        },
        body: JSON.stringify({
          service,
          model: model.modelName,
          prompt,
          category, // 传递分类，确保后端能正确归档
          negative_prompt: negativePrompt,
          size,
          count,
          resolution, // 传递画质参数
          aspect_ratio: aspectRatio // 传递比例参数
        })
      });

      const data = await resp.json();
      if (!resp.ok) throw new Error(data?.message || 'Backend request failed');

      // Handle Async Response
      if (data.status === 'submitted' && data.job_id) {
        return this.pollTaskGroup(data.job_id, prompt);
      }

      const urls = Array.isArray(data?.urls)
        ? (data.urls as string[]).filter(Boolean)
        : (typeof data?.url === 'string' && data.url ? [data.url as string] : []);
      if (urls.length === 0) return null;
      return { urls, prompt };
    } catch (error) {
      console.error("[Backend] Error:", error);
      throw error;
    }
  }

  private async pollTaskGroup(jobId: string, prompt: string): Promise<{urls: string[], prompt: string} | null> {
    const maxAttempts = 120; // 10 minutes (5s interval)
    let attempts = 0;
    
    while (attempts < maxAttempts) {
      await new Promise(resolve => setTimeout(resolve, 5000));
      attempts++;
      
      try {
        const resp = await fetch(`/api/tasks/group/${jobId}`);
        if (!resp.ok) continue;
        const status = await resp.json();
        
        if (status.ready && status.results) {
           const urls = status.results
             .filter((r: any) => r && r.status === 'success' && r.url)
             .map((r: any) => r.url);
           return { urls, prompt };
        }
      } catch (e) {
        console.error("Polling error", e);
      }
    }
    throw new Error("Task timeout");
  }

  private inferService(model: ModelInfo): 'wan' | 'z_image' {
    const name = (model?.modelName || '').toLowerCase();
    if (name.includes('z-image') || name.includes('z_image')) return 'z_image';
    return 'wan';
  }

  private mapAspectRatioToAliyun(ratio: string): string {
    const maps: Record<string, string> = {
      '1:1': '1024*1024',
      '16:9': '1280*720',
      '9:16': '720*1280',
      '4:3': '1024*768',
      '3:4': '768*1024',
      '2:3': '832*1216',
      '3:2': '1216*832',
      '21:9': '1536*640'
    };
    return maps[ratio] || '1024*1024';
  }

  private async getStableSessionId(): Promise<string> {
    const hourKey = new Date().toISOString().slice(0, 13); // YYYY-MM-DDTHH
    const cacheKey = `session_id_${hourKey}`;
    const cached = localStorage.getItem(cacheKey);
    if (cached && this.isUuid(cached)) return cached;
    const base = `${this.getUserId()}|${hourKey}`;
    const digestHex = await this.sha256Hex(base);
    const uuid = this.hexToUuidV5(digestHex);
    localStorage.setItem(cacheKey, uuid);
    return uuid;
  }

  private getUserId(): string {
    const uid = localStorage.getItem('user_id');
    return (uid && uid.trim()) ? uid.trim() : '-1';
  }

  private async sha256Hex(input: string): Promise<string> {
    const enc = new TextEncoder().encode(input);
    if (window.crypto && window.crypto.subtle) {
      const buf = await window.crypto.subtle.digest('SHA-256', enc);
      const arr = Array.from(new Uint8Array(buf));
      return arr.map(b => b.toString(16).padStart(2, '0')).join('');
    }
    // Fallback simple hash
    let h = 0;
    for (let i = 0; i < input.length; i++) {
      h = ((h << 5) - h) + input.charCodeAt(i);
      h |= 0;
    }
    return Math.abs(h).toString(16).padStart(32, '0').repeat(2).slice(0, 64);
  }

  private hexToUuidV5(hex: string): string {
    const clean = hex.slice(0, 32);
    const parts = [
      clean.slice(0, 8),
      clean.slice(8, 12),
      ((parseInt(clean.slice(12, 16), 16) & 0x0fff) | 0x5000).toString(16).padStart(4, '0'), // version 5
      ((parseInt(clean.slice(16, 20), 16) & 0x3fff) | 0x8000).toString(16).padStart(4, '0'), // RFC 4122 variant
      clean.slice(20, 32),
    ];
    return parts.join('-');
  }

  private isUuid(v: string): boolean {
    return /^[0-9a-f]{8}-[0-9a-f]{4}-[45][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i.test(v);
  }
}

export const geminiService = new ImageGenerationService();

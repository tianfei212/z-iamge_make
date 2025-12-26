
import { GoogleGenAI } from "@google/genai";
import { AspectRatio, Resolution, ModelInfo } from "../types";

const ALIYUN_API_KEY = "sk-f529fce2b0d44c54b8704bb96383a040";

export class ImageGenerationService {
  constructor() {}

  async translateText(text: string): Promise<string> {
    if (!text || text.trim().length === 0) return text;
    
    const ai = new GoogleGenAI({ apiKey: process.env.API_KEY });
    try {
      const response = await ai.models.generateContent({
        model: 'gemini-3-flash-preview',
        contents: `Translate the following text. If it is Chinese, translate to English. If it is English, translate to Chinese. Only return the translated text without any explanation: "${text}"`,
        config: {
            temperature: 0.1,
            topP: 0.1,
        }
      });
      return response.text?.trim() || text;
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
    model: ModelInfo
  ): Promise<{url: string, prompt: string} | null> {
    
    const finalPrompt = `
      ${commonSubject || ''} ${category}: ${specificPrompt}. 
      Style: ${globalStyle}. 
      High resolution, professional rendering.
    `.trim();

    if (model.provider === 'google') {
      return this.generateWithGemini(finalPrompt, negativePrompt, aspectRatio, resolution);
    } else {
      return this.generateWithAliyun(finalPrompt, negativePrompt, aspectRatio, model.modelName);
    }
  }

  private async generateWithGemini(
    prompt: string, 
    negativePrompt: string, 
    aspectRatio: AspectRatio, 
    resolution: Resolution
  ) {
    const ai = new GoogleGenAI({ apiKey: process.env.API_KEY });
    const instruction = `Generate image: ${prompt}. Negatives: ${negativePrompt}`;
    const modelName = resolution === '1K' ? 'gemini-2.5-flash-image' : 'gemini-3-pro-image-preview';

    try {
      const response = await ai.models.generateContent({
        model: modelName,
        contents: { parts: [{ text: instruction }] },
        config: {
          imageConfig: {
            aspectRatio: aspectRatio,
            ...(modelName === 'gemini-3-pro-image-preview' ? { imageSize: resolution } : {})
          }
        },
      });

      const part = response.candidates?.[0]?.content?.parts.find(p => p.inlineData);
      if (part?.inlineData) {
        return {
          url: `data:image/png;base64,${part.inlineData.data}`,
          prompt
        };
      }
      return null;
    } catch (error) {
      console.error("[Gemini] Error:", error);
      throw error;
    }
  }

  private async generateWithAliyun(
    prompt: string, 
    negativePrompt: string, 
    aspectRatio: string,
    modelName: string
  ) {
    const endpoint = 'https://dashscope.aliyuncs.com/api/v1/services/aigc/text2image/image-synthesis';
    
    try {
      const submitResponse = await fetch(endpoint, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${ALIYUN_API_KEY}`,
          'Content-Type': 'application/json',
          'X-DashScope-Async': 'enable'
        },
        body: JSON.stringify({
          model: modelName,
          input: {
            prompt: prompt,
            negative_prompt: negativePrompt
          },
          parameters: {
            size: this.mapAspectRatioToAliyun(aspectRatio),
            n: 1
          }
        })
      });

      const taskData = await submitResponse.json();
      if (!taskData.output?.task_id) throw new Error("Failed to submit Aliyun task");

      const taskId = taskData.output.task_id;

      let resultUrl = null;
      for (let i = 0; i < 30; i++) {
        await new Promise(r => setTimeout(r, 2000));
        const statusResponse = await fetch(`https://dashscope.aliyuncs.com/api/v1/tasks/${taskId}`, {
          headers: { 'Authorization': `Bearer ${ALIYUN_API_KEY}` }
        });
        const statusData = await statusResponse.json();
        
        if (statusData.output?.task_status === 'SUCCEEDED') {
          resultUrl = statusData.output.results[0].url;
          break;
        } else if (statusData.output?.task_status === 'FAILED') {
          throw new Error(`Aliyun task failed: ${statusData.output.message}`);
        }
      }

      if (resultUrl) {
        const imgBlob = await fetch(resultUrl).then(r => r.blob());
        const base64 = await new Promise((resolve) => {
          const reader = new FileReader();
          reader.onloadend = () => resolve(reader.result);
          reader.readAsDataURL(imgBlob);
        });
        return { url: base64 as string, prompt };
      }
      return null;
    } catch (error) {
      console.error("[Aliyun] Error:", error);
      throw error;
    }
  }

  private mapAspectRatioToAliyun(ratio: string): string {
    const maps: Record<string, string> = {
      '1:1': '1024*1024',
      '16:9': '1280*720',
      '9:16': '720*1280',
      '4:3': '1024*768',
      '3:4': '768*1024'
    };
    return maps[ratio] || '1024*1024';
  }
}

export const geminiService = new ImageGenerationService();

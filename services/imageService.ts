export interface ImageDetails {
  image: {
    id: string
    category: string
    filename: string
    timestamp: number
    originalUrl: string
    thumbUrl: string
    url: string
  }
  prompts: {
    positive: string | null
    negative: string | null
    base_prompt: string | null
    category_prompt: string | null
  }
  meta: {
    aspect_ratio?: string | null
    quality?: string | null
    model_name?: string | null
    created_at?: string | null
    status?: string | null
  }
}

export async function getImageDetails(params: { filename: string; category?: string }): Promise<ImageDetails> {
  const q = new URLSearchParams()
  if (params.category) q.set('category', params.category)
  const resp = await fetch(`/api/images/by-filename/${encodeURIComponent(params.filename)}/details?${q.toString()}`)
  if (!resp.ok) {
    throw new Error(`详情获取失败: ${resp.status}`)
  }
  return resp.json()
}

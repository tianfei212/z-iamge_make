import React, { useEffect, useState } from 'react';

interface GlobalSettings {
  common_subject: string;
  global_style: string;
  negative_prompt: string;
}

export const ConfigManagement: React.FC = () => {
  const [global, setGlobal] = useState<GlobalSettings>({ common_subject: '', global_style: '', negative_prompt: '' });
  const [savingGlobal, setSavingGlobal] = useState(false);
  const [enablePromptUpdateRequest, setEnablePromptUpdateRequest] = useState<boolean>(false);
  const [categories, setCategories] = useState<string[]>([]);
  const [newCategory, setNewCategory] = useState('');
  const [prompts, setPrompts] = useState<Record<string, string>>({});
  const [editingCat, setEditingCat] = useState<string | null>(null);
  const [editingPrompt, setEditingPrompt] = useState<string>('');
  const [err, setErr] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [savingAll, setSavingAll] = useState(false);
  const [models, setModels] = useState<Array<{id: string; name: string; provider: string; model_name: string; description?: string; enabled?: number}>>([]);
  const [modelLimits, setModelLimits] = useState<Record<string, number>>({});
  const [editingModelId, setEditingModelId] = useState<string | null>(null);
  const [modelDraft, setModelDraft] = useState<Partial<{name: string; provider: string; model_name: string; description?: string; enabled?: boolean}>>({});

  async function loadAll() {
    setLoading(true);
    setErr(null);
    try {
      const [g, c, p, m, flags] = await Promise.all([
        fetch('/api/config/global').then(r => r.json()),
        fetch('/api/categories').then(r => r.json()),
        fetch('/api/prompts').then(r => r.json()),
        fetch('/api/models').then(r => r.json()),
        fetch('/api/config/flags').then(r => r.json()).catch(() => ({ enable_prompt_update_request: false }))
      ]);
      setGlobal({
        common_subject: g.common_subject ?? '',
        global_style: g.global_style ?? '',
        negative_prompt: g.negative_prompt ?? '',
      });
      setCategories((c.categories || []) as string[]);
      setPrompts((p.prompts || {}) as Record<string, string>);
      const modelsList = (m.models || []) as any[];
      setModels(modelsList);
      setEnablePromptUpdateRequest(!!flags.enable_prompt_update_request);
      try {
        const resp = await fetch('/api/config/limits');
        if (resp.ok) {
          const ml = await resp.json();
          setModelLimits((ml.model_limits || {}) as Record<string, number>);
        } else {
          // fallback: derive defaults by provider
          const derived: Record<string, number> = {};
          for (const item of modelsList) {
            const mn = item?.model_name || '';
            const prov = String(item?.provider || '');
            derived[mn] = prov === 'z_image' ? 4 : 2;
          }
          setModelLimits(derived);
        }
      } catch {
        const derived: Record<string, number> = {};
        for (const item of modelsList) {
          const mn = item?.model_name || '';
          const prov = String(item?.provider || '');
          derived[mn] = prov === 'z_image' ? 4 : 2;
        }
        setModelLimits(derived);
      }
    } catch {
      setErr('加载失败');
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { loadAll(); }, []);

  async function saveGlobal() {
    setSavingGlobal(true);
    try {
      const resp = await fetch('/api/config/global', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(global)
      });
      if (!resp.ok) throw new Error('save failed');
    } catch {
      alert('保存失败：请稍后重试');
    } finally {
      setSavingGlobal(false);
    }
  }

  async function postWithRetry(url: string, body: any, attempts = 3, delayMs = 500): Promise<Response> {
    let lastErr: any = null;
    for (let i = 0; i < attempts; i++) {
      try {
        const resp = await fetch(url, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(body)
        });
        if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
        return resp;
      } catch (e) {
        lastErr = e;
        await new Promise(r => setTimeout(r, delayMs * Math.pow(2, i)));
      }
    }
    throw lastErr;
  }

  async function saveAll() {
    setSavingAll(true);
    const payload = {
      global,
      categories,
      prompts,
      model_limits: modelLimits,
      timestamp: new Date().toISOString(),
    };
    try {
      const resp = await postWithRetry('/api/config/update', payload, 3, 600);
      const data = await resp.json().catch(() => ({}));
      if (data?.global) setGlobal({
        common_subject: data.global.common_subject ?? global.common_subject,
        global_style: data.global.global_style ?? global.global_style,
        negative_prompt: data.global.negative_prompt ?? global.negative_prompt,
      });
      if (Array.isArray(data?.categories)) setCategories(data.categories);
      if (data?.prompts && typeof data.prompts === 'object') setPrompts(data.prompts);
      if (data?.model_limits && typeof data.model_limits === 'object') setModelLimits(data.model_limits);
      // show toast
      const { showToast } = await import('../components/Toast');
      showToast('配置已保存', 'success');
    } catch (e) {
      // fallback: try granular saves
      try {
        await saveGlobal();
        for (const cat of categories) {
          // ensure category exists
          await fetch('/api/categories', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name: cat })
          }).catch(() => {});
        }
        for (const [cat, prompt] of Object.entries(prompts)) {
          await fetch(`/api/prompts/${encodeURIComponent(cat)}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ prompt })
          }).catch(() => {});
        }
        // persist model limits via models endpoint
        try {
          const modelsResp = await fetch('/api/models');
          if (modelsResp.ok) {
            const mdata = await modelsResp.json();
            const arr = (mdata.models || []) as Array<any>;
            for (const item of arr) {
              const mn = item?.model_name;
              const id = item?.id;
              if (!mn || !id) continue;
              if (Object.prototype.hasOwnProperty.call(modelLimits, mn)) {
                await fetch(`/api/models/${encodeURIComponent(id)}`, {
                  method: 'PUT',
                  headers: {'Content-Type':'application/json'},
                  body: JSON.stringify({ max_limit: modelLimits[mn] })
                }).catch(() => {});
              }
            }
          }
        } catch {}
        const { showToast } = await import('../components/Toast');
        showToast('配置已部分保存（降级写入）', 'info');
      } catch {
        const { showToast } = await import('../components/Toast');
        showToast('保存失败：网络异常', 'error');
      }
    } finally {
      setSavingAll(false);
      await loadAll();
    }
  }

  async function addCategory() {
    const name = newCategory.trim();
    if (!name) {
      alert('分类名称为必填项');
      return;
    }
    try {
      const resp = await fetch('/api/categories', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name })
      });
      if (!resp.ok) throw new Error('create failed');
      setNewCategory('');
      await loadAll();
    } catch {
      alert('创建分类失败');
    }
  }

  async function deleteCategory(name: string) {
    if (!confirm(`确认删除分类 "${name}"？`)) return;
    try {
      const resp = await fetch(`/api/categories/${encodeURIComponent(name)}`, { method: 'DELETE' });
      if (!resp.ok) throw new Error('delete failed');
      try {
        await fetch(`/api/prompts/${encodeURIComponent(name)}`, { method: 'DELETE' });
      } catch {}
      try {
        await fetch('/api/config/reload', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ reason: 'delete_category', category: name }) });
      } catch {}
      const { showToast } = await import('../components/Toast');
      showToast(`已删除分类 ${name}`, 'success');
      await loadAll();
    } catch {
      alert('删除分类失败');
    }
  }

  function startEditPrompt(cat: string) {
    setEditingCat(cat);
    setEditingPrompt(prompts[cat] || '');
  }

  async function savePrompt(cat: string) {
    try {
      const resp = await fetch(`/api/prompts/${encodeURIComponent(cat)}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ prompt: editingPrompt })
      });
      if (!resp.ok) throw new Error('update failed');
      setEditingCat(null);
      setEditingPrompt('');
      await loadAll();
    } catch {
      alert('更新提示词失败');
    }
  }

  async function removePrompt(cat: string) {
    if (!confirm(`确认删除分类 "${cat}" 的提示词？`)) return;
    try {
      const resp = await fetch(`/api/prompts/${encodeURIComponent(cat)}`, { method: 'DELETE' });
      if (!resp.ok) throw new Error('delete failed');
      await loadAll();
    } catch {
      alert('删除提示词失败');
    }
  }

  async function createPrompt(cat: string, prompt: string) {
    if (!cat.trim()) {
      alert('分类名称为必填项');
      return;
    }
    try {
      const resp = await fetch('/api/prompts', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ category: cat.trim(), prompt: prompt.trim() })
      });
      if (!resp.ok) throw new Error('create failed');
      await loadAll();
    } catch {
      alert('创建提示词失败');
    }
  }

  async function createModel(m: {id: string; name: string; provider: string; model_name: string; description?: string}) {
    try {
      const resp = await fetch('/api/models', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(m)
      });
      if (!resp.ok) throw new Error('create model failed');
      await loadAll();
    } catch {
      alert('创建模型失败');
    }
  }

  function startEditModel(id: string, m: any) {
    setEditingModelId(id);
    setModelDraft({
      name: m.name,
      provider: m.provider,
      model_name: m.model_name,
      description: m.description,
      enabled: !!(m.enabled ?? 1),
    });
  }

  async function saveModel(id: string) {
    try {
      const payload: any = {...modelDraft};
      if (typeof payload.enabled === 'boolean') {
        payload.enabled = payload.enabled ? 1 : 0;
      }
      const resp = await fetch(`/api/models/${encodeURIComponent(id)}`, {
        method: 'PUT',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(payload)
      });
      if (!resp.ok) throw new Error('update model failed');
      setEditingModelId(null);
      setModelDraft({});
      await loadAll();
    } catch {
      alert('更新模型失败');
    }
  }

  async function removeModel(id: string) {
    if (!confirm('确认删除该模型？')) return;
    try {
      const resp = await fetch(`/api/models/${encodeURIComponent(id)}`, { method: 'DELETE' });
      if (!resp.ok) throw new Error('delete model failed');
      await loadAll();
    } catch {
      alert('删除模型失败');
    }
  }

  return (
    <div className="flex flex-col h-screen text-gray-100">
      <header className="px-6 py-4 bg-[#08090a] border-b border-gray-800 flex items-center justify-between">
        <h1 className="text-sm font-bold tracking-wider">配置管理</h1>
        <div className="flex items-center gap-3">
          <button
            onClick={saveAll}
            disabled={savingAll}
            className="px-3 py-2 bg-blue-600 hover:bg-blue-500 disabled:opacity-50 text-white rounded text-xs flex items-center gap-2"
          >
            {savingAll && (
              <svg className="animate-spin h-3 w-3" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="3" fill="none"></circle>
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V1C5.373 1 1 5.373 1 12h3zm2 5.291A7.962 7.962 0 016 12H3c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
              </svg>
            )}
            保存所有配置
          </button>
          <div className="text-xs text-zinc-400">路径 /config-management</div>
        </div>
      </header>
      <main className="flex-1 p-6 space-y-6">
        {err && <div className="text-xs text-red-400">错误：{err}</div>}
        <section className="bg-[#141518] border border-[#2e3035] rounded-lg p-4">
          <h2 className="text-sm font-bold mb-3">全局配置</h2>
          <div className="grid grid-cols-3 gap-4">
            <div>
              <label className="text-[10px] text-zinc-500 block mb-1">通用主体</label>
              <textarea
                value={global.common_subject}
                onChange={(e) => setGlobal({ ...global, common_subject: e.target.value })}
                className="w-full bg-black border border-zinc-800 rounded p-2 text-xs min-h-[80px] outline-none"
              />
            </div>
            <div>
              <label className="text-[10px] text-zinc-500 block mb-1">风格</label>
              <input
                value={global.global_style}
                onChange={(e) => setGlobal({ ...global, global_style: e.target.value })}
                className="w-full bg-black border border-zinc-800 rounded p-2 text-xs outline-none"
              />
            </div>
            <div>
              <label className="text-[10px] text-zinc-500 block mb-1">负面提示词</label>
              <input
                value={global.negative_prompt}
                onChange={(e) => setGlobal({ ...global, negative_prompt: e.target.value })}
                className="w-full bg-black border border-zinc-800 rounded p-2 text-xs outline-none"
              />
            </div>
          </div>
          <div className="mt-3">
            <button
              onClick={saveGlobal}
              disabled={savingGlobal}
              className="px-3 py-2 bg-blue-600 hover:bg-blue-500 disabled:opacity-50 text-white rounded text-xs"
            >
              保存
            </button>
          </div>
          <div className="mt-4 border-t border-[#2e3035] pt-4">
            <h3 className="text-xs font-bold mb-2">功能开关</h3>
            <label className="flex items-center gap-2 text-xs">
              <input
                type="checkbox"
                checked={enablePromptUpdateRequest}
                onChange={(e) => setEnablePromptUpdateRequest(e.target.checked)}
              />
              <span>启用提示词继承（每张图片使用上一张精炼正向提示词）</span>
            </label>
            <div className="mt-2">
              <button
                className="px-3 py-2 bg-blue-600 hover:bg-blue-500 text-white rounded text-xs"
                onClick={async () => {
                  try {
                    const resp = await fetch('/api/config/flags', {
                      method: 'PUT',
                      headers: { 'Content-Type': 'application/json' },
                      body: JSON.stringify({ enable_prompt_update_request: enablePromptUpdateRequest })
                    });
                    if (!resp.ok) throw new Error('save flags failed');
                    const { showToast } = await import('../components/Toast');
                    showToast('功能开关已保存', 'success');
                    await fetch('/api/config/reload', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ reason: 'save_flags' }) }).catch(() => {});
                  } catch {
                    const { showToast } = await import('../components/Toast');
                    showToast('保存功能开关失败', 'error');
                  }
                }}
              >
                保存功能开关
              </button>
            </div>
          </div>
        </section>

        <section className="bg-[#141518] border border-[#2e3035] rounded-lg p-4">
          <h2 className="text-sm font-bold mb-3">模型配置</h2>
          <div className="overflow-x-auto mb-3">
            <table className="min-w-full text-left text-xs">
              <thead>
                <tr className="text-zinc-400">
                  <th className="py-2 px-2 border-b border-[#2e3035]">ID</th>
                  <th className="py-2 px-2 border-b border-[#2e3035]">名称</th>
                  <th className="py-2 px-2 border-b border-[#2e3035]">Provider</th>
                  <th className="py-2 px-2 border-b border-[#2e3035]">ModelName</th>
                  <th className="py-2 px-2 border-b border-[#2e3035]">描述</th>
                  <th className="py-2 px-2 border-b border-[#2e3035]">启用</th>
                  <th className="py-2 px-2 border-b border-[#2e3035]">上限</th>
                  <th className="py-2 px-2 border-b border-[#2e3035]">操作</th>
                </tr>
              </thead>
              <tbody>
                {models.map(m => (
                  <tr key={m.id} className="text-zinc-200">
                    <td className="py-2 px-2 border-b border-[#2e3035]">{m.id}</td>
                    <td className="py-2 px-2 border-b border-[#2e3035]">
                      {editingModelId === m.id ? (
                        <input className="bg-black border border-zinc-800 rounded p-1 text-xs outline-none w-full"
                          value={String(modelDraft.name ?? '')}
                          onChange={(e) => setModelDraft({...modelDraft, name: e.target.value})}
                        />
                      ) : m.name}
                    </td>
                    <td className="py-2 px-2 border-b border-[#2e3035]">
                      {editingModelId === m.id ? (
                        <input className="bg-black border border-zinc-800 rounded p-1 text-xs outline-none w-full"
                          value={String(modelDraft.provider ?? '')}
                          onChange={(e) => setModelDraft({...modelDraft, provider: e.target.value})}
                        />
                      ) : m.provider}
                    </td>
                    <td className="py-2 px-2 border-b border-[#2e3035]">
                      {editingModelId === m.id ? (
                        <input className="bg-black border border-zinc-800 rounded p-1 text-xs outline-none w-full"
                          value={String(modelDraft.model_name ?? '')}
                          onChange={(e) => setModelDraft({...modelDraft, model_name: e.target.value})}
                        />
                      ) : m.model_name}
                    </td>
                    <td className="py-2 px-2 border-b border-[#2e3035]">
                      {editingModelId === m.id ? (
                        <input className="bg-black border border-zinc-800 rounded p-1 text-xs outline-none w-full"
                          value={String(modelDraft.description ?? '')}
                          onChange={(e) => setModelDraft({...modelDraft, description: e.target.value})}
                        />
                      ) : (m.description || '')}
                    </td>
                    <td className="py-2 px-2 border-b border-[#2e3035]">
                      {editingModelId === m.id ? (
                        <input type="checkbox" checked={!!modelDraft.enabled}
                          onChange={(e) => setModelDraft({...modelDraft, enabled: e.target.checked})}
                        />
                      ) : (m.enabled ?? 1) ? '是' : '否'}
                    </td>
                    <td className="py-2 px-2 border-b border-[#2e3035]">
                      <input
                        type="number"
                        className="bg-black border border-zinc-800 rounded p-1 text-xs outline-none w-20"
                        value={modelLimits[m.model_name] ?? (m as any).max_limit ?? 0}
                        onChange={(e) => setModelLimits({...modelLimits, [m.model_name]: Math.max(0, parseInt(e.target.value) || 0)})}
                      />
                    </td>
                    <td className="py-2 px-2 border-b border-[#2e3035]">
                      {editingModelId === m.id ? (
                        <div className="flex gap-2">
                          <button onClick={() => saveModel(m.id)} className="px-2 py-1 bg-blue-600 hover:bg-blue-500 text-white rounded">保存</button>
                          <button onClick={() => { setEditingModelId(null); setModelDraft({}); }} className="px-2 py-1 bg-zinc-700 hover:bg-zinc-600 text-white rounded">取消</button>
                        </div>
                      ) : (
                        <div className="flex gap-2">
                          <button onClick={() => startEditModel(m.id, m)} className="px-2 py-1 bg-zinc-700 hover:bg-zinc-600 text-white rounded">编辑</button>
                          <button onClick={() => removeModel(m.id)} className="px-2 py-1 bg-red-600 hover:bg-red-500 text-white rounded">删除</button>
                        </div>
                      )}
                    </td>
                  </tr>
                ))}
                {models.length === 0 && (
                  <tr>
                    <td colSpan={8} className="py-4 text-center text-zinc-500">暂无模型</td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
          <div className="mt-2">
            <button
              className="px-3 py-2 bg-blue-600 hover:bg-blue-500 text-white rounded text-xs"
              onClick={async () => {
                try {
                  const resp = await fetch('/api/config/update', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({ model_limits: modelLimits, timestamp: new Date().toISOString() })
                  });
                  if (!resp.ok) throw new Error('save limits failed');
                  const { showToast } = await import('../components/Toast');
                  showToast('模型上限已保存', 'success');
                  await loadAll();
                } catch {
                  const { showToast } = await import('../components/Toast');
                  showToast('保存模型上限失败', 'error');
                }
              }}
            >
              保存模型上限
            </button>
          </div>
          <div className="grid grid-cols-5 gap-3">
            <input placeholder="ID" className="bg-black border border-zinc-800 rounded p-2 text-xs outline-none" id="newModelId" />
            <input placeholder="名称" className="bg-black border border-zinc-800 rounded p-2 text-xs outline-none" id="newModelName" />
            <input placeholder="Provider" className="bg-black border border-zinc-800 rounded p-2 text-xs outline-none" id="newModelProvider" />
            <input placeholder="ModelName" className="bg-black border border-zinc-800 rounded p-2 text-xs outline-none" id="newModelModelName" />
            <input placeholder="描述(可选)" className="bg-black border border-zinc-800 rounded p-2 text-xs outline-none" id="newModelDesc" />
          </div>
          <div className="mt-2">
            <button
              className="px-3 py-2 bg-blue-600 hover:bg-blue-500 text-white rounded text-xs"
              onClick={() => {
                const id = (document.getElementById('newModelId') as HTMLInputElement)?.value || '';
                const name = (document.getElementById('newModelName') as HTMLInputElement)?.value || '';
                const provider = (document.getElementById('newModelProvider') as HTMLInputElement)?.value || '';
                const model_name = (document.getElementById('newModelModelName') as HTMLInputElement)?.value || '';
                const description = (document.getElementById('newModelDesc') as HTMLInputElement)?.value || '';
                if (!id.trim() || !name.trim() || !provider.trim() || !model_name.trim()) {
                  alert('ID、名称、Provider、ModelName 为必填项');
                  return;
                }
                createModel({ id: id.trim(), name: name.trim(), provider: provider.trim(), model_name: model_name.trim(), description: description.trim() });
              }}
            >
              创建模型
            </button>
          </div>
        </section>

        <section className="bg-[#141518] border border-[#2e3035] rounded-lg p-4">
          <h2 className="text-sm font-bold mb-3">分类管理</h2>
          <div className="flex gap-3 mb-3">
            <input
              value={newCategory}
              onChange={(e) => setNewCategory(e.target.value)}
              placeholder="新分类名称"
              className="bg-black border border-zinc-800 rounded p-2 text-xs outline-none"
            />
            <button onClick={addCategory} className="px-3 py-2 bg-blue-600 hover:bg-blue-500 text-white rounded text-xs">添加</button>
          </div>
          <div className="flex flex-wrap gap-2">
            {categories.map(cat => (
              <div key={cat} className="flex items-center gap-2 bg-zinc-900 border border-zinc-800 rounded px-2 py-1">
                <span className="text-xs text-zinc-300">{cat}</span>
                <button onClick={() => deleteCategory(cat)} className="text-[10px] text-red-400 hover:text-red-300">删除</button>
              </div>
            ))}
            {categories.length === 0 && <span className="text-xs text-zinc-500">暂无分类</span>}
          </div>
        </section>

        <section className="bg-[#141518] border border-[#2e3035] rounded-lg p-4">
          <div className="flex items-center justify-between mb-3">
            <h2 className="text-sm font-bold">提示词配置</h2>
            {loading && <span className="text-[10px] text-zinc-500">加载中...</span>}
          </div>
          <div className="overflow-x-auto">
            <table className="min-w-full text-left text-xs">
              <thead>
                <tr className="text-zinc-400">
                  <th className="py-2 px-2 border-b border-[#2e3035]">分类</th>
                  <th className="py-2 px-2 border-b border-[#2e3035]">提示词</th>
                  <th className="py-2 px-2 border-b border-[#2e3035]">操作</th>
                </tr>
              </thead>
              <tbody>
                {Object.keys(prompts).map(cat => (
                  <tr key={cat} className="text-zinc-200">
                    <td className="py-2 px-2 border-b border-[#2e3035]">{cat}</td>
                    <td className="py-2 px-2 border-b border-[#2e3035]">
                      {editingCat === cat ? (
                        <input
                          value={editingPrompt}
                          onChange={(e) => setEditingPrompt(e.target.value)}
                          className="bg-black border border-zinc-800 rounded p-1 text-xs outline-none w-full"
                        />
                      ) : prompts[cat]}
                    </td>
                    <td className="py-2 px-2 border-b border-[#2e3035]">
                      {editingCat === cat ? (
                        <div className="flex gap-2">
                          <button onClick={() => savePrompt(cat)} className="px-2 py-1 bg-blue-600 hover:bg-blue-500 text-white rounded">保存</button>
                          <button onClick={() => { setEditingCat(null); setEditingPrompt(''); }} className="px-2 py-1 bg-zinc-700 hover:bg-zinc-600 text-white rounded">取消</button>
                        </div>
                      ) : (
                        <div className="flex gap-2">
                          <button onClick={() => startEditPrompt(cat)} className="px-2 py-1 bg-zinc-700 hover:bg-zinc-600 text-white rounded">编辑</button>
                          <button onClick={() => removePrompt(cat)} className="px-2 py-1 bg-red-600 hover:bg-red-500 text-white rounded">删除</button>
                        </div>
                      )}
                    </td>
                  </tr>
                ))}
                {Object.keys(prompts).length === 0 && (
                  <tr>
                    <td colSpan={3} className="py-4 text-center text-zinc-500">暂无提示词配置</td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
          <div className="mt-4">
            <h3 className="text-xs font-bold text-zinc-400 mb-2">新增提示词</h3>
            <div className="grid grid-cols-3 gap-3">
              <select
                className="bg-black border border-zinc-800 rounded p-2 text-xs outline-none"
                defaultValue=""
                id="newPromptCat"
              >
                <option value="" disabled>选择分类</option>
                {categories.map(cat => <option key={cat} value={cat}>{cat}</option>)}
              </select>
              <input
                className="bg-black border border-zinc-800 rounded p-2 text-xs outline-none"
                placeholder="提示词内容"
                id="newPromptText"
              />
              <button
                className="px-3 py-2 bg-blue-600 hover:bg-blue-500 text-white rounded text-xs"
                onClick={() => {
                  const cat = (document.getElementById('newPromptCat') as HTMLSelectElement)?.value || '';
                  const txt = (document.getElementById('newPromptText') as HTMLInputElement)?.value || '';
                  createPrompt(cat, txt);
                }}
              >
                创建
              </button>
            </div>
          </div>
        </section>
      </main>
    </div>
  );
};

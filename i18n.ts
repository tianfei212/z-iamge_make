type Messages = Record<string, string>;

const zhCN: Messages = {
  'app.title': '中影AI 图像生成',
  'app.subtitle': 'MULTI-PROVIDER ENGINE V3.2',
  'modal.title': '功能面板',
  'modal.open_config': '打开配置管理',
  'modal.close': '关闭',
};

const enUS: Messages = {
  'app.title': 'GEMINI PRODUCTION',
  'app.subtitle': 'MULTI-PROVIDER ENGINE V3.2',
  'modal.title': 'Actions',
  'modal.open_config': 'Open Config Management',
  'modal.close': 'Close',
};

function detectLocale(): 'zh-CN' | 'en-US' {
  const saved = localStorage.getItem('locale');
  if (saved === 'zh-CN' || saved === 'en-US') return saved;
  const lang = navigator.language || 'en';
  return lang.toLowerCase().startsWith('zh') ? 'zh-CN' : 'en-US';
}

const catalogs: Record<string, Messages> = {
  'zh-CN': zhCN,
  'en-US': enUS,
};

export function t(key: string): string {
  const locale = detectLocale();
  const dict = catalogs[locale] || enUS;
  return dict[key] ?? key;
}


const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api/v1';

const request = async (path, options = {}) => {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    headers: {
      'Content-Type': 'application/json',
      ...options.headers
    },
    ...options
  });

  const data = await response.json().catch(() => ({}));

  if (!response.ok) {
    const error = new Error(data.detail || response.statusText || '请求失败');
    error.status = response.status;
    error.payload = data;
    throw error;
  }

  return data;
};

export const api = {
  // ========== 报告相关 ==========
  createReport: payload => request('/tasks/report', { method: 'POST', body: JSON.stringify(payload) }),
  createPPT: payload => request('/tasks/ppt', { method: 'POST', body: JSON.stringify(payload) }),
  getTaskStatus: taskId => request(`/tasks/${encodeURIComponent(taskId)}`),
  getTaskResult: taskId => request(`/tasks/${encodeURIComponent(taskId)}/result`),
  cancelTask: taskId => request(`/tasks/${encodeURIComponent(taskId)}`, { method: 'DELETE' }),
  listTasks: params => {
    const query = new URLSearchParams();
    if (params?.status) query.set('status', params.status);
    if (params?.task_type) query.set('task_type', params.task_type);
    if (params?.limit) query.set('limit', String(params.limit));
    const queryString = query.toString();
    return request(queryString ? `/tasks?${queryString}` : '/tasks');
  },

  // ========== 数据分析接口 ==========
  /**
   * 用户上传文件分析（CSV/文本） - 直接返回 HTML 报告
   * POST /api/v1/data_analysis/file
   * @param {Object} payload - { query, file_name, file_type, file_content, use_llm }
   */
  analyzeFile: payload => request('/data_analysis/file', { method: 'POST', body: JSON.stringify(payload) }),

  /**
   * 金融数据分析（基于搜索结果） - 返回结构化结果和 ECharts 配置
   * POST /api/v1/data_analysis/charts
   * @param {Object} payload - { query, search_results, rag_pack, use_mock }
   */
  analyzeCharts: payload => request('/data_analysis/charts', { method: 'POST', body: JSON.stringify(payload) }),

  // ========== RAG 检索接口 ==========
  retrieveKnowledge: payload => request('/rag/retrieve', { method: 'POST', body: JSON.stringify(payload) }),
};

// 任务类型常量
export const TASK_TYPES = {
  REPORT: 'report',
  PPT: 'ppt',
  ANALYSIS: 'analysis',
  RAG: 'rag',
  // 金融分析（搜索+分析）
  FINANCIAL_ANALYSIS: 'financial_analysis'
};

// 交付物类型（与 deliverable 参数对应）
export const DELIVERABLE_TYPES = {
  REPORT: 'report',     // 综合分析报告
  PPT: 'ppt',           // 演示文稿
  ANALYSIS_HTML: 'analysis_html',  // 仅生成分析 HTML（搜索+分析）
  ANALYSIS_JSON: 'analysis_json',  // 仅生成分析 JSON（搜索+分析）
};

export const SYSTEM_MODULES = [
  {
    id: 'report',
    name: '研究报告',
    description: '生成商业/学术/技术报告，可选择是否添加金融数据分析',
    defaultTaskType: 'report',
    color: '#2563eb',
    accent: '#eff6ff',
  },
  {
    id: 'ppt',
    name: '演示文稿',
    description: '生成可导出 PPTX 的演示文稿，可选择是否添加金融数据分析',
    defaultTaskType: 'ppt',
    color: '#059669',
    accent: '#ecfdf5',
  },
  {
    id: 'file_analysis',
    name: '文件数据分析',
    description: '上传 CSV/TXT 文件，生成独立的数据分析报告（含可视化图表）',
    defaultTaskType: 'file_analysis',
    color: '#d97706',
    accent: '#fffbeb',
  },
  {
    id: 'financial_analysis',
    name: '金融分析',
    description: '基于网页搜索，提取并分析金融数据，生成可视化报告',
    defaultTaskType: 'financial_analysis',
    color: '#7c3aed',
    accent: '#f5f3ff',
  },
  {
    id: 'rag',
    name: '知识检索',
    description: '基于 RAG 的知识库检索与问答',
    defaultTaskType: 'rag',
    color: '#7c3aed',
    accent: '#f5f3ff',
  },
];

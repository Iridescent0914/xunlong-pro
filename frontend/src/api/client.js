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
  createReport: payload => request('/tasks/report', { method: 'POST', body: JSON.stringify(payload) }),
  createFiction: payload => request('/tasks/fiction', { method: 'POST', body: JSON.stringify(payload) }),
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
  // 预留：数据分析接口占位
  createAnalysisTask: async payload => {
    console.warn('[API] 数据分析接口暂未接入，将返回模拟任务 ID', payload);
    return {
      task_id: `analysis_${Date.now()}`,
      status: 'pending',
      message: '数据分析任务已创建（占位返回）'
    };
  },
  // 预留：RAG 检索接口占位
  retrieveKnowledge: async payload => {
    console.warn('[API] RAG 检索接口暂未接入，将返回模拟结果', payload);
    return {
      status: 'success',
      query: payload?.query || '',
      answer: 'RAG 检索结果将接入后替换为实际召回内容。',
      references: []
    };
  }
};

export const SYSTEM_MODULES = [
  {
    id: 'report',
    name: '研究报告',
    description: '生成商业/学术/技术报告',
    defaultTaskType: 'report'
  },
  {
    id: 'fiction',
    name: '小说创作',
    description: '生成多风格多章节小说',
    defaultTaskType: 'fiction'
  },
  {
    id: 'ppt',
    name: '演示文稿',
    description: '生成可导出 PPTX 的演示文稿',
    defaultTaskType: 'ppt'
  },
  {
    id: 'analysis',
    name: '数据分析',
    description: '数据分析 agent 占位模块',
    defaultTaskType: 'analysis',
    placeholder: true
  },
  {
    id: 'rag',
    name: '知识检索',
    description: 'RAG 检索模块占位入口',
    defaultTaskType: 'rag',
    placeholder: true
  }
];

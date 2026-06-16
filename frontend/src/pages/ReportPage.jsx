import { useState } from 'react';
import { api } from '../api/client';
import TaskMonitor from '../components/TaskMonitor';

const reportTypes = [
  { value: 'comprehensive', label: '综合报告' },
  { value: 'daily', label: '日报' },
  { value: 'analysis', label: '分析报告' },
  { value: 'research', label: '研究报告' }
];

const depths = [
  { value: 'surface', label: '浅层' },
  { value: 'medium', label: '标准' },
  { value: 'deep', label: '深度' }
];

export default function ReportPage({ onSubmitTask }) {
  const [form, setForm] = useState({
    query: '',
    report_type: 'comprehensive',
    search_depth: 'deep',
    max_results: 20,
    output_format: 'html',
    html_template: 'enhanced_professional',
    html_theme: 'light',
    input_file: null
  });

  const updateField = (field, value) => {
    setForm(prev => ({ ...prev, [field]: value }));
  };

  const handleSubmit = async event => {
    event.preventDefault();
    const payload = {
      ...form,
      max_results: Number(form.max_results)
    };
    const response = await api.createReport(payload);
    onSubmitTask?.(response);
  };

  return (
    <div className="grid gap-6 lg:grid-cols-5">
      <form onSubmit={handleSubmit} className="space-y-5 rounded-3xl border border-white/60 bg-white/80 p-6 shadow-sm lg:col-span-3">
        <div>
          <h2 className="text-lg font-semibold text-gray-900">研究报告生成</h2>
          <p className="text-sm text-gray-500">输入研究主题，系统将自动检索并生成结构化报告。</p>
        </div>

        <label className="block space-y-1">
          <span className="text-sm font-medium text-gray-700">研究主题</span>
          <textarea
            value={form.query}
            onChange={event => updateField('query', event.target.value)}
            placeholder="例如：2025年生成式 AI 行业趋势分析"
            className="w-full rounded-2xl border border-gray-200 px-4 py-3 text-sm focus:border-blue-500 focus:outline-none"
            rows={3}
            required
          />
        </label>

        <div className="grid gap-4 sm:grid-cols-2">
          <label className="space-y-1">
            <span className="text-sm font-medium text-gray-700">报告类型</span>
            <select
              value={form.report_type}
              onChange={event => updateField('report_type', event.target.value)}
              className="w-full rounded-2xl border border-gray-200 px-4 py-3 text-sm focus:border-blue-500 focus:outline-none"
            >
              {reportTypes.map(option => (
                <option key={option.value} value={option.value}>{option.label}</option>
              ))}
            </select>
          </label>

          <label className="space-y-1">
            <span className="text-sm font-medium text-gray-700">检索深度</span>
            <select
              value={form.search_depth}
              onChange={event => updateField('search_depth', event.target.value)}
              className="w-full rounded-2xl border border-gray-200 px-4 py-3 text-sm focus:border-blue-500 focus:outline-none"
            >
              {depths.map(option => (
                <option key={option.value} value={option.value}>{option.label}</option>
              ))}
            </select>
          </label>
        </div>

        <label className="block space-y-1">
          <span className="text-sm font-medium text-gray-700">最大检索数量</span>
          <input
            type="number"
            min={1}
            max={50}
            value={form.max_results}
            onChange={event => updateField('max_results', event.target.value)}
            className="w-full rounded-2xl border border-gray-200 px-4 py-3 text-sm focus:border-blue-500 focus:outline-none"
          />
        </label>

        <div className="grid gap-4 sm:grid-cols-3">
          <label className="space-y-1">
            <span className="text-sm font-medium text-gray-700">输出格式</span>
            <select
              value={form.output_format}
              onChange={event => updateField('output_format', event.target.value)}
              className="w-full rounded-2xl border border-gray-200 px-4 py-3 text-sm focus:border-blue-500 focus:outline-none"
            >
              <option value="html">HTML</option>
              <option value="md">Markdown</option>
            </select>
          </label>

          <label className="space-y-1">
            <span className="text-sm font-medium text-gray-700">HTML 模板</span>
            <input
              value={form.html_template}
              onChange={event => updateField('html_template', event.target.value)}
              className="w-full rounded-2xl border border-gray-200 px-4 py-3 text-sm focus:border-blue-500 focus:outline-none"
            />
          </label>

          <label className="space-y-1">
            <span className="text-sm font-medium text-gray-700">主题</span>
            <select
              value={form.html_theme}
              onChange={event => updateField('html_theme', event.target.value)}
              className="w-full rounded-2xl border border-gray-200 px-4 py-3 text-sm focus:border-blue-500 focus:outline-none"
            >
              <option value="light">浅色</option>
              <option value="dark">深色</option>
            </select>
          </label>
        </div>

        <label className="block space-y-1">
          <span className="text-sm font-medium text-gray-700">上下文文档</span>
          <input
            type="file"
            accept=".txt,.pdf,.docx"
            onChange={event => updateField('input_file', event.target.files?.[0] ?? null)}
            className="w-full rounded-2xl border border-dashed border-gray-300 px-4 py-3 text-sm"
          />
          <span className="text-xs text-gray-500">可上传 .txt / .pdf / .docx 作为生成前提。</span>
        </label>

        <button
          type="submit"
          className="w-full rounded-2xl bg-blue-600 px-4 py-3 text-sm font-semibold text-white shadow-sm hover:bg-blue-700"
        >
          创建报告任务
        </button>
      </form>

      <div className="space-y-4 lg:col-span-2">
        <TaskMonitor taskId={null} onTaskCompleted={() => undefined} />
      </div>
    </div>
  );
}

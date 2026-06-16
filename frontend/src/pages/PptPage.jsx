import { useState } from 'react';
import { api } from '../api/client';

const styles = [
  { value: 'business', label: '商务' },
  { value: 'academic', label: '学术' },
  { value: 'creative', label: '创意' },
  { value: 'simple', label: '简约' }
];

const themes = [
  { value: 'corporate-blue', label: '企业蓝' },
  { value: 'default', label: '默认' },
  { value: 'minimal', label: '极简' }
];

export default function PptPage({ onSubmitTask }) {
  const [form, setForm] = useState({
    query: '',
    slides: 12,
    style: 'business',
    theme: 'corporate-blue',
    depth: 'medium',
    speech_notes: '',
    input_file: null
  });

  const updateField = (field, value) => {
    setForm(prev => ({ ...prev, [field]: value }));
  };

  const handleSubmit = async event => {
    event.preventDefault();
    const payload = {
      ...form,
      slides: Number(form.slides)
    };
    const response = await api.createPPT(payload);
    onSubmitTask?.(response);
  };

  return (
    <div className="grid gap-6 lg:grid-cols-5">
      <form onSubmit={handleSubmit} className="space-y-5 rounded-3xl border border-white/60 bg-white/80 p-6 shadow-sm lg:col-span-3">
        <div>
          <h2 className="text-lg font-semibold text-gray-900">演示文稿生成</h2>
          <p className="text-sm text-gray-500">输入演讲主题与风格偏好，生成可导出为 PPTX 的演示文稿。</p>
        </div>

        <label className="block space-y-1">
          <span className="text-sm font-medium text-gray-700">演讲主题</span>
          <textarea
            value={form.query}
            onChange={event => updateField('query', event.target.value)}
            placeholder="例如：2025 年公司战略发布会"
            className="w-full rounded-2xl border border-gray-200 px-4 py-3 text-sm focus:border-emerald-500 focus:outline-none"
            rows={3}
            required
          />
        </label>

        <div className="grid gap-4 sm:grid-cols-2">
          <label className="space-y-1">
            <span className="text-sm font-medium text-gray-700">页数</span>
            <input
              type="number"
              min={4}
              max={50}
              value={form.slides}
              onChange={event => updateField('slides', event.target.value)}
              className="w-full rounded-2xl border border-gray-200 px-4 py-3 text-sm focus:border-emerald-500 focus:outline-none"
            />
          </label>

          <label className="space-y-1">
            <span className="text-sm font-medium text-gray-700">深度</span>
            <select
              value={form.depth}
              onChange={event => updateField('depth', event.target.value)}
              className="w-full rounded-2xl border border-gray-200 px-4 py-3 text-sm focus:border-emerald-500 focus:outline-none"
            >
              <option value="surface">概览</option>
              <option value="medium">标准</option>
              <option value="deep">深度</option>
            </select>
          </label>
        </div>

        <div className="grid gap-4 sm:grid-cols-2">
          <label className="space-y-1">
            <span className="text-sm font-medium text-gray-700">风格</span>
            <select
              value={form.style}
              onChange={event => updateField('style', event.target.value)}
              className="w-full rounded-2xl border border-gray-200 px-4 py-3 text-sm focus:border-emerald-500 focus:outline-none"
            >
              {styles.map(option => (
                <option key={option.value} value={option.value}>{option.label}</option>
              ))}
            </select>
          </label>

          <label className="space-y-1">
            <span className="text-sm font-medium text-gray-700">主题</span>
            <select
              value={form.theme}
              onChange={event => updateField('theme', event.target.value)}
              className="w-full rounded-2xl border border-gray-200 px-4 py-3 text-sm focus:border-emerald-500 focus:outline-none"
            >
              {themes.map(option => (
                <option key={option.value} value={option.value}>{option.label}</option>
              ))}
            </select>
          </label>
        </div>

        <label className="block space-y-1">
          <span className="text-sm font-medium text-gray-700">演说稿说明</span>
          <textarea
            value={form.speech_notes}
            onChange={event => updateField('speech_notes', event.target.value)}
            placeholder="用于生成每页幻灯片的演讲稿"
            className="w-full rounded-2xl border border-gray-200 px-4 py-3 text-sm focus:border-emerald-500 focus:outline-none"
            rows={2}
          />
        </label>

        <label className="block space-y-1">
          <span className="text-sm font-medium text-gray-700">参考文档</span>
          <input
            type="file"
            accept=".txt,.pdf,.docx"
            onChange={event => updateField('input_file', event.target.files?.[0] ?? null)}
            className="w-full rounded-2xl border border-dashed border-gray-300 px-4 py-3 text-sm"
          />
        </label>

        <button
          type="submit"
          className="w-full rounded-2xl bg-emerald-600 px-4 py-3 text-sm font-semibold text-white shadow-sm hover:bg-emerald-700"
        >
          创建 PPT 任务
        </button>
      </form>

      <div className="space-y-4 lg:col-span-2">
        <div className="rounded-2xl border border-emerald-100 bg-emerald-50/70 p-5 text-sm text-emerald-900">
          系统会自动生成大纲、配色和内容结构，最终可导出为 PPTX 文件。
        </div>
      </div>
    </div>
  );
}

import { useState } from 'react';
import { api } from '../api/client';

const genres = [
  { value: 'mystery', label: '悬疑' },
  { value: 'scifi', label: '科幻' },
  { value: 'fantasy', label: '玄幻' },
  { value: 'horror', label: '恐怖' },
  { value: 'romance', label: '言情' },
  { value: 'wuxia', label: '武侠' }
];

const lengths = [
  { value: 'short', label: '短篇' },
  { value: 'medium', label: '中篇' },
  { value: 'long', label: '长篇' }
];

const viewpoints = [
  { value: 'first', label: '第一人称' },
  { value: 'third', label: '第三人称' },
  { value: 'omniscient', label: '全知视角' }
];

export default function FictionPage({ onSubmitTask }) {
  const [form, setForm] = useState({
    query: '',
    genre: 'mystery',
    length: 'short',
    viewpoint: 'first',
    constraints: [],
    output_format: 'html',
    html_template: 'novel',
    html_theme: 'sepia',
    input_file: null
  });

  const updateField = (field, value) => {
    setForm(prev => ({ ...prev, [field]: value }));
  };

  const handleSubmit = async event => {
    event.preventDefault();
    const payload = {
      ...form,
      constraints: Array.isArray(form.constraints) ? form.constraints : []
    };
    const response = await api.createFiction(payload);
    onSubmitTask?.(response);
  };

  return (
    <div className="grid gap-6 lg:grid-cols-5">
      <form onSubmit={handleSubmit} className="space-y-5 rounded-3xl border border-white/60 bg-white/80 p-6 shadow-sm lg:col-span-3">
        <div>
          <h2 className="text-lg font-semibold text-gray-900">小说创作</h2>
          <p className="text-sm text-gray-500">提供核心创意和风格要求，系统将自动扩写为小说初稿。</p>
        </div>

        <label className="block space-y-1">
          <span className="text-sm font-medium text-gray-700">故事创意</span>
          <textarea
            value={form.query}
            onChange={event => updateField('query', event.target.value)}
            placeholder="例如：未来城市中一名AI维修员发现城市核心程序正在自我进化"
            className="w-full rounded-2xl border border-gray-200 px-4 py-3 text-sm focus:border-fuchsia-500 focus:outline-none"
            rows={3}
            required
          />
        </label>

        <div className="grid gap-4 sm:grid-cols-2">
          <label className="space-y-1">
            <span className="text-sm font-medium text-gray-700">题材</span>
            <select
              value={form.genre}
              onChange={event => updateField('genre', event.target.value)}
              className="w-full rounded-2xl border border-gray-200 px-4 py-3 text-sm focus:border-fuchsia-500 focus:outline-none"
            >
              {genres.map(option => (
                <option key={option.value} value={option.value}>{option.label}</option>
              ))}
            </select>
          </label>

          <label className="space-y-1">
            <span className="text-sm font-medium text-gray-700">篇幅</span>
            <select
              value={form.length}
              onChange={event => updateField('length', event.target.value)}
              className="w-full rounded-2xl border border-gray-200 px-4 py-3 text-sm focus:border-fuchsia-500 focus:outline-none"
            >
              {lengths.map(option => (
                <option key={option.value} value={option.value}>{option.label}</option>
              ))}
            </select>
          </label>
        </div>

        <label className="space-y-1">
          <span className="text-sm font-medium text-gray-700">视角</span>
          <select
            value={form.viewpoint}
            onChange={event => updateField('viewpoint', event.target.value)}
            className="w-full rounded-2xl border border-gray-200 px-4 py-3 text-sm focus:border-fuchsia-500 focus:outline-none"
          >
            {viewpoints.map(option => (
              <option key={option.value} value={option.value}>{option.label}</option>
            ))}
          </select>
        </label>

        <label className="block space-y-1">
          <span className="text-sm font-medium text-gray-700">约束条件</span>
          <textarea
            value={form.constraints.join('\n')}
            onChange={event => updateField('constraints', event.target.value.split('\n').filter(Boolean))}
            placeholder="每行一个约束，例如：禁止使用超能力设定"
            className="w-full rounded-2xl border border-gray-200 px-4 py-3 text-sm focus:border-fuchsia-500 focus:outline-none"
            rows={3}
          />
        </label>

        <label className="block space-y-1">
          <span className="text-sm font-medium text-gray-700">上下文文档</span>
          <input
            type="file"
            accept=".txt,.pdf,.docx"
            onChange={event => updateField('input_file', event.target.files?.[0] ?? null)}
            className="w-full rounded-2xl border border-dashed border-gray-300 px-4 py-3 text-sm"
          />
        </label>

        <button
          type="submit"
          className="w-full rounded-2xl bg-fuchsia-600 px-4 py-3 text-sm font-semibold text-white shadow-sm hover:bg-fuchsia-700"
        >
          创建小说任务
        </button>
      </form>

      <div className="space-y-4 lg:col-span-2">
        <div className="rounded-2xl border border-dashed border-fuchsia-200 bg-fuchsia-50/60 p-5 text-sm text-fuchsia-900">
          小说生成需要更长的运行时间，请通过右侧任务状态监控查看进度。
        </div>
      </div>
    </div>
  );
}

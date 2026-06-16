import { useState } from 'react';
import { api } from '../api/client';

export default function RagPlaceholder() {
  const [query, setQuery] = useState('');
  const [filters, setFilters] = useState({
    knowledge_base: 'default',
    top_k: 5,
    enable_rerank: true
  });
  const [response, setResponse] = useState(null);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async event => {
    event.preventDefault();
    setLoading(true);
    setError(null);
    setResponse(null);

    try {
      const payload = {
        query,
        filters,
        context: {
          retrieval_mode: 'hybrid',
          enable_summarization: true,
          enable_system_integration: true
        }
      };
      const data = await api.retrieveKnowledge(payload);
      setResponse(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="grid gap-6 lg:grid-cols-5">
      <form onSubmit={handleSubmit} className="space-y-5 rounded-3xl border border-violet-200 bg-violet-50/70 p-6 shadow-sm lg:col-span-3">
        <div>
          <h2 className="text-lg font-semibold text-violet-900">RAG 知识检索（占位）</h2>
          <p className="text-sm text-violet-900/80">后续由组员接入 RAG 检索模块和系统集成；当前保留检索表单与结果占位展示。</p>
        </div>

        <label className="block space-y-1">
          <span className="text-sm font-medium text-violet-900">检索问题</span>
          <textarea
            value={query}
            onChange={event => setQuery(event.target.value)}
            placeholder="描述你想从知识库中检索的信息"
            className="w-full rounded-2xl border border-violet-200 bg-white px-4 py-3 text-sm focus:border-violet-500 focus:outline-none"
            rows={3}
            required
          />
        </label>

        <div className="grid gap-4 sm:grid-cols-2">
          <label className="space-y-1">
            <span className="text-sm font-medium text-violet-900">知识库</span>
            <select
              value={filters.knowledge_base}
              onChange={event => setFilters(prev => ({ ...prev, knowledge_base: event.target.value }))}
              className="w-full rounded-2xl border border-violet-200 bg-white px-4 py-3 text-sm focus:border-violet-500 focus:outline-none"
            >
              <option value="default">默认知识库</option>
              <option value="internal">内部文档库</option>
              <option value="product">产品文档库</option>
            </select>
          </label>

          <label className="space-y-1">
            <span className="text-sm font-medium text-violet-900">Top-K</span>
            <input
              type="number"
              min={1}
              max={20}
              value={filters.top_k}
              onChange={event => setFilters(prev => ({ ...prev, top_k: Number(event.target.value) }))}
              className="w-full rounded-2xl border border-violet-200 bg-white px-4 py-3 text-sm focus:border-violet-500 focus:outline-none"
            />
          </label>
        </div>

        <label className="flex items-center gap-2 text-sm text-violet-900">
          <input
            type="checkbox"
            checked={filters.enable_rerank}
            onChange={event => setFilters(prev => ({ ...prev, enable_rerank: event.target.checked }))}
          />
          启用重排序
        </label>

        <button
          type="submit"
          disabled={loading}
          className="w-full rounded-2xl bg-violet-600 px-4 py-3 text-sm font-semibold text-white shadow-sm hover:bg-violet-700 disabled:opacity-70"
        >
          {loading ? '检索中...' : '发起检索'}
        </button>

        {error ? <p className="text-sm text-red-600">错误：{error}</p> : null}
      </form>

      <div className="space-y-4 lg:col-span-2">
        {response ? (
          <div className="rounded-2xl border border-violet-200 bg-white/80 p-5 text-sm text-violet-900 shadow-sm">
            <p className="font-semibold">检索结果占位</p>
            <p className="mt-2 whitespace-pre-wrap">{response.answer}</p>
            {Array.isArray(response.references) && response.references.length ? (
              <ul className="mt-3 list-disc space-y-1 pl-5 text-violet-800">
                {response.references.map((item, index) => (
                  <li key={index}>{item}</li>
                ))}
              </ul>
            ) : null}
          </div>
        ) : (
          <div className="rounded-2xl border border-dashed border-violet-200 bg-white/60 p-5 text-sm text-violet-900">
            请在左侧输入检索问题，系统将在此展示结果占位。
          </div>
        )}

        <div className="rounded-2xl border border-violet-100 bg-white/80 p-5 text-sm text-violet-900">
          <p className="font-semibold">系统集成预留字段</p>
          <ul className="mt-2 list-disc space-y-1 pl-5">
            <li>retrieveKnowledge(payload)</li>
            <li>payload.filters.knowledge_base</li>
            <li>payload.context.retrieval_mode：hybrid / dense / sparse</li>
            <li>payload.context.enable_summarization</li>
            <li>payload.context.enable_system_integration</li>
          </ul>
        </div>
      </div>
    </div>
  );
}

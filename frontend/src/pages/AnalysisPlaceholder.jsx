import { useState } from 'react';
import { api } from '../api/client';
import TaskMonitor from '../components/TaskMonitor';

const sampleQueries = [
  '上传销售 Excel 后，自动生成月度分析摘要',
  '生成用户增长关键指标趋势',
  '对数据库查询结果进行异常检测'
];

export default function AnalysisPlaceholder({ onSubmitTask }) {
  const [query, setQuery] = useState('');
  const [dataSource, setDataSource] = useState('excel');
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
        data_source: dataSource,
        context: {
          analysis_mode: 'auto',
          visualization: true,
          rag_enabled: true
        }
      };
      const data = await api.createAnalysisTask(payload);
      setResponse(data);
      onSubmitTask?.(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="grid gap-6 lg:grid-cols-5">
      <form onSubmit={handleSubmit} className="space-y-5 rounded-3xl border border-amber-200 bg-amber-50/70 p-6 shadow-sm lg:col-span-3">
        <div>
          <h2 className="text-lg font-semibold text-amber-900">数据分析 Agent（占位）</h2>
          <p className="text-sm text-amber-800/80">后续将由组员接入数据分析 agent；当前界面先保留任务创建入口和状态监控。</p>
        </div>

        <label className="block space-y-1">
          <span className="text-sm font-medium text-amber-900">分析目标</span>
          <textarea
            value={query}
            onChange={event => setQuery(event.target.value)}
            placeholder="描述希望从数据中分析出的结论"
            className="w-full rounded-2xl border border-amber-200 bg-white px-4 py-3 text-sm focus:border-amber-500 focus:outline-none"
            rows={3}
            required
          />
          <div className="flex flex-wrap gap-2">
            {sampleQueries.map(item => (
              <button
                key={item}
                type="button"
                onClick={() => setQuery(item)}
                className="rounded-full border border-amber-200 px-3 py-1 text-xs text-amber-800 hover:bg-amber-100"
              >
                {item}
              </button>
            ))}
          </div>
        </label>

        <label className="space-y-1">
          <span className="text-sm font-medium text-amber-900">数据来源</span>
          <select
            value={dataSource}
            onChange={event => setDataSource(event.target.value)}
            className="w-full rounded-2xl border border-amber-200 bg-white px-4 py-3 text-sm focus:border-amber-500 focus:outline-none"
          >
            <option value="excel">Excel</option>
            <option value="database">数据库</option>
            <option value="upload">上传文件</option>
          </select>
        </label>

        <label className="block space-y-1">
          <span className="text-sm font-medium text-amber-900">上传数据文件</span>
          <input
            type="file"
            accept=".csv,.xlsx,.xls,.json"
            className="w-full rounded-2xl border border-dashed border-amber-300 bg-white px-4 py-3 text-sm"
          />
        </label>

        <button
          type="submit"
          disabled={loading}
          className="w-full rounded-2xl bg-amber-600 px-4 py-3 text-sm font-semibold text-white shadow-sm hover:bg-amber-700 disabled:opacity-70"
        >
          {loading ? '创建数据分析任务...' : '创建数据分析任务'}
        </button>

        {error ? <p className="text-sm text-red-600">错误：{error}</p> : null}
        {response ? <p className="text-sm text-amber-900">返回：{JSON.stringify(response)}</p> : null}
      </form>

      <div className="space-y-4 lg:col-span-2">
        <TaskMonitor taskId={response?.task_id} onTaskCompleted={() => undefined} />
        <div className="rounded-2xl border border-amber-100 bg-white/80 p-5 text-sm text-amber-900">
          <p className="font-semibold">预留接口字段</p>
          <ul className="mt-2 list-disc space-y-1 pl-5">
            <li>createAnalysisTask(payload)</li>
            <li>payload.query：分析目标</li>
            <li>payload.data_source：excel / database / upload</li>
            <li>payload.context.analysis_mode：auto / diagnostic / predictive</li>
            <li>payload.context.visualization：是否生成图表</li>
          </ul>
        </div>
      </div>
    </div>
  );
}

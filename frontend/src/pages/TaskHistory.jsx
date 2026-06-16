import { useEffect, useState } from 'react';
import { api } from '../api/client';

export default function TaskHistory({ onSelectTask }) {
  const [tasks, setTasks] = useState([]);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(true);

  const fetchTasks = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.listTasks({ limit: 50 });
      setTasks(data.tasks || []);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchTasks();
  }, []);

  return (
    <div className="rounded-3xl border border-white/60 bg-white/80 p-6 shadow-sm">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-lg font-semibold text-gray-900">任务记录</h2>
          <p className="text-sm text-gray-500">查看最近创建的生成任务，点击可继续查看结果。</p>
        </div>
        <button
          onClick={fetchTasks}
          className="rounded-2xl border border-gray-200 px-4 py-2 text-xs text-gray-700 hover:bg-gray-50"
        >
          刷新
        </button>
      </div>

      {error ? <p className="mt-4 text-sm text-red-600">加载失败：{error}</p> : null}

      {loading ? <p className="mt-4 text-sm text-gray-500">正在加载任务列表...</p> : null}

      {!loading && !tasks.length ? (
        <p className="mt-4 text-sm text-gray-500">暂无任务记录。</p>
      ) : null}

      <ul className="mt-4 space-y-3">
        {tasks.map(task => (
          <li key={task.task_id}>
            <button
              onClick={() => onSelectTask?.(task.task_id)}
              className="flex w-full items-center justify-between rounded-2xl border border-gray-100 px-4 py-3 text-left hover:border-blue-200 hover:bg-blue-50"
            >
              <span className="space-y-1">
                <span className="block text-sm font-medium text-gray-900">{task.query || '未命名任务'}</span>
                <span className="block text-xs text-gray-500">{task.task_type} · {task.created_at}</span>
              </span>
              <span className="text-xs text-gray-500">{task.progress ?? 0}%</span>
            </button>
          </li>
        ))}
      </ul>
    </div>
  );
}

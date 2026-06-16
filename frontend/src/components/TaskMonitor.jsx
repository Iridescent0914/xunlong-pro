import { useEffect, useRef, useState } from 'react';
import { api } from '../api/client';

export default function TaskMonitor({ taskId, onTaskCompleted, compact }) {
  const [status, setStatus] = useState(null);
  const [error, setError] = useState(null);
  const timerRef = useRef(null);

  const fetchStatus = async () => {
    if (!taskId) return;
    try {
      const data = await api.getTaskStatus(taskId);
      setStatus(data);
      if (data.status === 'completed') {
        onTaskCompleted?.(data);
      }
    } catch (err) {
      setError(err.message);
    }
  };

  useEffect(() => {
    setStatus(null);
    setError(null);
    fetchStatus();

    timerRef.current = window.setInterval(fetchStatus, 3000);
    return () => window.clearInterval(timerRef.current);
  }, [taskId]);

  if (!taskId) {
    return <p className="text-sm text-gray-500">暂无运行中的任务。</p>;
  }

  if (error) {
    return <p className="text-sm text-red-600">加载失败：{error}</p>;
  }

  if (!status) {
    return <p className="text-sm text-gray-500">正在读取任务状态...</p>;
  }

  const progress = typeof status.progress === 'number' ? status.progress : 0;
  const statusColors = {
    pending: 'bg-gray-200 text-gray-700',
    running: 'bg-blue-100 text-blue-700',
    completed: 'bg-emerald-100 text-emerald-700',
    failed: 'bg-red-100 text-red-700',
    cancelled: 'bg-gray-200 text-gray-700'
  };

  return (
    <div className="rounded-2xl border border-white/70 bg-white/80 p-5 shadow-sm">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-xs text-gray-500">任务 ID</p>
          <p className="font-mono text-sm text-gray-800">{status.task_id}</p>
        </div>
        <span className={`rounded-full px-3 py-1 text-xs font-medium ${statusColors[status.status] || 'bg-gray-100 text-gray-700'}`}>
          {status.status}
        </span>
      </div>

      <div className="mt-4">
        <div className="flex items-center justify-between text-xs text-gray-500">
          <span>{status.current_step || '处理中'}</span>
          <span>{progress}%</span>
        </div>
        <div className="mt-2 h-2 rounded-full bg-gray-100">
          <div className="h-full rounded-full bg-blue-500 transition-all" style={{ width: `${progress}%` }} />
        </div>
      </div>

      {compact ? null : (
        <div className="mt-4 space-y-1 text-xs text-gray-600">
          <p>类型：{status.task_type}</p>
          <p>创建时间：{status.created_at}</p>
          {status.started_at ? <p>开始时间：{status.started_at}</p> : null}
          {status.completed_at ? <p>完成时间：{status.completed_at}</p> : null}
          {status.error ? <p className="text-red-600">错误：{status.error}</p> : null}
        </div>
      )}
    </div>
  );
}

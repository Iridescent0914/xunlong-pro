import { useState } from 'react';
import Sidebar from './components/Sidebar';
import TaskMonitor from './components/TaskMonitor';
import ReportPage from './pages/ReportPage';
import FictionPage from './pages/FictionPage';
import PptPage from './pages/PptPage';
import AnalysisPlaceholder from './pages/AnalysisPlaceholder';
import RagPlaceholder from './pages/RagPlaceholder';
import TaskHistory from './pages/TaskHistory';

const pages = {
  report: ReportPage,
  fiction: FictionPage,
  ppt: PptPage,
  analysis: AnalysisPlaceholder,
  rag: RagPlaceholder
};

export default function App() {
  const [activeModule, setActiveModule] = useState('report');
  const [currentTaskId, setCurrentTaskId] = useState(null);
  const Page = pages[activeModule] || ReportPage;

  const handleSubmitTask = response => {
    setCurrentTaskId(response?.task_id || null);
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-indigo-50 via-white to-pink-50">
      <header className="border-b border-white/60 bg-white/70 backdrop-blur">
        <div className="mx-auto flex max-w-7xl items-center justify-between px-6 py-4">
          <div>
            <p className="text-xl font-bold text-gray-900">XunLong 可视化工作台</p>
            <p className="text-sm text-gray-500">基于现有 API 预留数据分析与 RAG 接口</p>
          </div>
          <a
            href="http://localhost:8000/docs"
            target="_blank"
            rel="noreferrer"
            className="rounded-2xl border border-gray-200 px-4 py-2 text-xs text-gray-700 hover:bg-gray-50"
          >
            查看 API 文档
          </a>
        </div>
      </header>

      <main className="mx-auto max-w-7xl px-6 py-8">
        <div className="grid gap-8 lg:grid-cols-12">
          <div className="lg:col-span-3">
            <Sidebar activeModule={activeModule} onSelectModule={setActiveModule} />
            <div className="mt-6">
              <TaskHistory onSelectTask={setCurrentTaskId} />
            </div>
          </div>

          <div className="space-y-6 lg:col-span-9">
            <Page onSubmitTask={handleSubmitTask} />
            <TaskMonitor taskId={currentTaskId} onTaskCompleted={() => undefined} />
          </div>
        </div>
      </main>

      <footer className="border-t border-white/60 bg-white/70 py-6 text-center text-xs text-gray-500">
        前端原型已完成；数据分析 agent、RAG 检索与系统集成接口可在此基础上继续接入。
      </footer>
    </div>
  );
}

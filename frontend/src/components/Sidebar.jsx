import { SYSTEM_MODULES } from '../api/client';

const moduleMeta = {
  report: { icon: '📄', activeClass: 'border-blue-500 bg-blue-50 text-blue-900' },
  fiction: { icon: '📚', activeClass: 'border-fuchsia-500 bg-fuchsia-50 text-fuchsia-900' },
  ppt: { icon: '🎬', activeClass: 'border-emerald-500 bg-emerald-50 text-emerald-900' },
  analysis: { icon: '📈', activeClass: 'border-amber-500 bg-amber-50 text-amber-900' },
  rag: { icon: '🧠', activeClass: 'border-violet-500 bg-violet-50 text-violet-900' }
};

export default function Sidebar({ activeModule, onSelectModule }) {
  return (
    <aside className="w-full rounded-3xl border border-white/60 bg-white/80 p-5 shadow-lg backdrop-blur">
      <div className="space-y-2">
        {SYSTEM_MODULES.map(module => {
          const meta = moduleMeta[module.id] || {};
          const isActive = activeModule === module.id;

          return (
            <button
              key={module.id}
              onClick={() => onSelectModule(module.id)}
              className={`flex w-full items-center gap-3 rounded-2xl border px-4 py-3 text-left transition ${
                isActive
                  ? `border-solid shadow-sm ${meta.activeClass || 'border-gray-900 bg-gray-900 text-white'}`
                  : 'border-transparent bg-white/60 text-gray-600 hover:border-gray-200 hover:bg-white'
              }`}
            >
              <span className="text-xl">{meta.icon || '🧩'}</span>
              <span className="flex flex-col">
                <span className="text-sm font-semibold">{module.name}</span>
                <span className="text-xs text-gray-500">{module.description}</span>
              </span>
              {module.placeholder ? <span className="ml-auto text-xs text-gray-400">占位</span> : null}
            </button>
          );
        })}
      </div>
    </aside>
  );
}

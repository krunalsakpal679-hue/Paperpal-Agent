// frontend/src/components/pipeline/AgentProgress.jsx
import React from 'react';
import { Check, Loader, FileText, Search, Zap, BarChart3, Clock } from 'lucide-react';

const AGENTS = [
    { id: 'ingesting', title: 'Ingest', icon: FileText },
    { id: 'parsing', title: 'Parse', icon: Search },
    { id: 'interpreting', title: 'Interpret', icon: Zap },
    { id: 'transforming', title: 'Transform', icon: SparklesIcon },
    { id: 'validating', title: 'Validate', icon: BarChart3 },
];

function SparklesIcon(props) {
    return (
        <svg
            xmlns="http://www.w3.org/2000/svg"
            width="24" height="24"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
            {...props}
        >
            <path d="m12 3-1.912 5.813a2 2 0 0 1-1.275 1.275L3 12l5.813 1.912a2 2 0 0 1 1.275 1.275L12 21l1.912-5.813a2 2 0 0 1 1.275-1.275L21 12l-5.813-1.912a2 2 0 0 1-1.275-1.275L12 3Z" />
            <path d="M5 3v4" /><path d="M19 17v4" /><path d="M3 5h4" /><path d="M17 19h4" />
        </svg>
    );
}

export default function AgentProgress({ events, currentAgent, progressPct }) {
    const getStageStatus = (agentId) => {
        const activeIndex = AGENTS.findIndex((a) => a.id === currentAgent);
        const targetIndex = AGENTS.findIndex((a) => a.id === agentId);

        if (targetIndex < activeIndex) return 'done';
        if (targetIndex === activeIndex) return 'active';
        return 'pending';
    };

    return (
        <div className="w-full flex flex-col gap-10 py-4 animate-in">
            {/* Pills Container */}
            <div className="grid grid-cols-1 md:grid-cols-5 gap-4">
                {AGENTS.map((agent, i) => {
                    const status = getStageStatus(agent.id);
                    return (
                        <div
                            key={agent.id}
                            className={`relative flex flex-col items-center gap-3 p-4 rounded-2xl border transition-all duration-500 ${status === 'done'
                                ? 'bg-emerald-50 border-emerald-100'
                                : status === 'active'
                                    ? 'bg-indigo-50 border-indigo-200 ring-2 ring-indigo-500/20'
                                    : 'bg-slate-50 border-slate-100 opacity-60'
                                }`}
                        >
                            <div
                                className={`w-10 h-10 rounded-xl flex items-center justify-center transition-all duration-500 ${status === 'done'
                                    ? 'bg-emerald-500 text-white shadow-lg shadow-emerald-500/30'
                                    : status === 'active'
                                        ? 'bg-indigo-500 text-white shadow-lg shadow-indigo-500/30'
                                        : 'bg-slate-200 text-slate-500'
                                    }`}
                            >
                                {status === 'done' ? <Check className="w-5 h-5" /> : <agent.icon className={`w-5 h-5 ${status === 'active' ? 'animate-pulse' : ''}`} />}
                            </div>
                            <div className="text-center">
                                <p className={`text-xs font-bold uppercase tracking-wider ${status === 'done' ? 'text-emerald-700' : status === 'active' ? 'text-indigo-700' : 'text-slate-400'
                                    }`}>
                                    {agent.title}
                                </p>
                                <p className="text-[10px] text-slate-500 font-medium">Stage {i + 1}</p>
                            </div>
                        </div>
                    );
                })}
            </div>

            {/* Progress Bar Container */}
            <div className="space-y-3">
                <div className="flex justify-between items-end px-1">
                    <div className="flex items-center gap-2">
                        <Loader className="w-4 h-4 text-indigo-500 animate-spin" />
                        <span className="text-sm font-bold text-slate-700">Currently: {AGENTS.find(a => a.id === currentAgent)?.title || 'Initializing'}</span>
                    </div>
                    <span className="text-sm font-extrabold text-indigo-600 tabular-nums">{progressPct}%</span>
                </div>
                <div className="w-full h-4 bg-slate-200 rounded-full overflow-hidden shadow-inner">
                    <div
                        className="h-full bg-gradient-to-r from-indigo-500 via-indigo-600 to-indigo-700 rounded-full transition-all duration-700 ease-out relative"
                        style={{ width: `${progressPct}%` }}
                    >
                        <div className="absolute inset-0 bg-white/20 animate-pulse"></div>
                    </div>
                </div>
            </div>

            {/* Log Feed */}
            <div className="w-full bg-slate-900 rounded-2xl p-6 shadow-xl border border-slate-800 overflow-hidden group">
                <div className="flex items-center gap-2 mb-4 text-slate-400 font-mono text-xs uppercase tracking-widest border-b border-white/5 pb-2">
                    <Clock className="w-3 h-3" />
                    Execution Logs
                </div>
                <div className="h-[160px] overflow-y-auto font-mono text-xs space-y-2 scrollbar-none">
                    {events.slice().reverse().slice(0, 10).map((event) => (
                        <div key={`${event.id}-${event.timestamp}`} className="flex gap-4 animate-in slide-in-from-left-2 transition-opacity duration-300">
                            <span className="text-slate-600 whitespace-nowrap">[{new Date(event.timestamp).toLocaleTimeString()}]</span>
                            <span className={`font-bold transition-colors ${event.status === 'completed' ? 'text-emerald-400' : 'text-indigo-400'
                                }`}>
                                {event.agent?.toUpperCase() || 'SYSTEM'}
                            </span>
                            <span className="text-slate-300 opacity-90">{event.message}</span>
                        </div>
                    ))}
                    {events.length === 0 && (
                        <div className="text-slate-600 italic">Waiting for agents to report status...</div>
                    )}
                </div>
            </div>
        </div>
    );
}

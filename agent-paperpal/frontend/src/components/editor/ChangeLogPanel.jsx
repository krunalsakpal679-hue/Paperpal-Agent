// frontend/src/components/editor/ChangeLogPanel.jsx
import React, { useState } from 'react';
import { Search, Filter, Info, AlertCircle, CheckCircle, ChevronDown, ChevronRight, Hash } from 'lucide-react';

const SEVERITY_ICONS = {
    info: <Info className="w-4 h-4 text-blue-500" />,
    warning: <AlertCircle className="w-4 h-4 text-amber-500" />,
    error: <AlertCircle className="w-4 h-4 text-red-500" />,
    success: <CheckCircle className="w-4 h-4 text-emerald-500" />,
};

export default function ChangeLogPanel({ changeLog = [] }) {
    const [searchTerm, setSearchTerm] = useState('');
    const [expandedItems, setExpandedItems] = useState({});

    const toggleExpand = (id) => {
        setExpandedItems(prev => ({ ...prev, [id]: !prev[id] }));
    };

    const filteredLogs = changeLog.filter(entry =>
        entry.element_type?.toLowerCase().includes(searchTerm.toLowerCase()) ||
        entry.rule_ref?.toLowerCase().includes(searchTerm.toLowerCase())
    );

    return (
        <div className="card-primary h-[calc(100vh-18rem)] flex flex-col p-8 border-slate-200 animate-in slide-in-from-left-5 duration-700">
            <div className="flex flex-col gap-6 mb-8">
                <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                        <h2 className="text-xl font-display font-black text-slate-900">Change Log</h2>
                        <span className="badge-primary px-3 py-1 font-black tabular-nums">{changeLog.length}</span>
                    </div>
                    <div className="flex items-center gap-2 px-3 py-1 bg-slate-100 rounded-lg text-xs font-black text-slate-500 uppercase tracking-widest">
                        <Filter className="w-3 h-3" />
                        Audited
                    </div>
                </div>

                <div className="relative group">
                    <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400 group-hover:text-indigo-500 transition-colors" />
                    <input
                        type="text"
                        placeholder="Search changes by rule or element..."
                        className="w-full bg-slate-50 border border-slate-200 rounded-xl py-3 pl-12 pr-4 text-sm font-medium focus:ring-4 focus:ring-indigo-500/10 focus:border-indigo-500 transition-all outline-none"
                        value={searchTerm}
                        onChange={(e) => setSearchTerm(e.target.value)}
                    />
                </div>
            </div>

            <div className="flex-grow overflow-y-auto space-y-4 pr-2 scrollbar-thin">
                {filteredLogs.length > 0 ? (
                    filteredLogs.map((entry, idx) => {
                        const isExpanded = expandedItems[idx];
                        return (
                            <div
                                key={idx}
                                className={`group border rounded-2xl p-5 transition-all duration-300 transform-gpu ${isExpanded ? 'border-indigo-200 bg-indigo-50/20 shadow-xl' : 'border-slate-100 hover:border-slate-300 hover:bg-slate-50'
                                    }`}
                            >
                                <div className="flex items-start gap-4 cursor-pointer select-none" onClick={() => toggleExpand(idx)}>
                                    <div className="mt-1 flex-shrink-0">
                                        {SEVERITY_ICONS[entry.severity] || SEVERITY_ICONS.info}
                                    </div>
                                    <div className="flex-grow min-w-0 space-y-2">
                                        <div className="flex items-center flex-wrap gap-2 pr-6">
                                            <span className="text-xs font-black uppercase text-indigo-700 tracking-wider flex items-center gap-1">
                                                <Hash className="w-3 h-3 opacity-50" />
                                                {entry.element_type}
                                            </span>
                                            <span className="text-xs font-bold text-slate-400 bg-slate-100 px-2 py-0.5 rounded italic">
                                                {entry.rule_ref}
                                            </span>
                                        </div>
                                        <p className="text-sm font-semibold text-slate-900 truncate leading-relaxed">
                                            {entry.description || `Modified ${entry.element_type} according to journal standards.`}
                                        </p>
                                    </div>
                                    <div className="absolute right-4 top-1/2 -translate-y-1/2 transition-transform duration-300">
                                        {isExpanded ? <ChevronDown className="w-5 h-5 text-indigo-500" /> : <ChevronRight className="w-5 h-5 text-slate-300 group-hover:text-indigo-400" />}
                                    </div>
                                </div>

                                {isExpanded && (
                                    <div className="mt-6 pt-6 border-t border-indigo-100/50 space-y-4 animate-in slide-in-from-top-2 duration-300">
                                        <div className="grid grid-cols-2 gap-6 relative">
                                            <div className="absolute left-1/2 top-4 bottom-4 w-px bg-indigo-100/50 -translate-x-1/2" />

                                            <div className="space-y-2">
                                                <label className="text-[10px] font-black uppercase tracking-widest text-slate-400">Original Fragment</label>
                                                <div className="text-xs font-medium text-slate-500 bg-red-50/30 p-4 rounded-xl border border-red-100/50 leading-relaxed font-mono italic">
                                                    "{entry.original_text || '...'}"
                                                </div>
                                            </div>

                                            <div className="space-y-2">
                                                <label className="text-[10px] font-black uppercase tracking-widest text-indigo-400">Transformed Output</label>
                                                <div className="text-xs font-black text-indigo-700 bg-indigo-50/50 p-4 rounded-xl border border-indigo-200/50 leading-relaxed font-mono">
                                                    "{entry.transformed_text || '...'}"
                                                </div>
                                            </div>
                                        </div>

                                        <div className="flex items-center justify-between pt-2">
                                            <span className="text-[10px] font-bold text-slate-400">Transformer ID: <code className="text-indigo-500 uppercase">{entry.transformer_id || 'SystemAgent'}</code></span>
                                        </div>
                                    </div>
                                )}
                            </div>
                        );
                    })
                ) : (
                    <div className="py-24 text-center space-y-4">
                        <Search className="w-12 h-12 text-slate-200 mx-auto" />
                        <p className="text-sm font-bold text-slate-400">No matching changes found.</p>
                    </div>
                )}
            </div>
        </div>
    );
}

// frontend/src/components/results/ComplianceGauge.jsx
import React from 'react';
import { RadialBarChart, RadialBar, ResponsiveContainer, PolarAngleAxis } from 'recharts';

export default function ComplianceGauge({ overallScore = 0, categoryScores = {} }) {
    const data = [{ name: 'score', value: overallScore, fill: overallScore > 85 ? '#10b981' : overallScore > 60 ? '#f59e0b' : '#ef4444' }];

    const categories = [
        { label: 'Citations', key: 'citations', score: categoryScores.citations || 0 },
        { label: 'References', key: 'references', score: categoryScores.references || 0 },
        { label: 'Headings', key: 'headings', score: categoryScores.headings || 0 },
        { label: 'Abstract', key: 'abstract', score: categoryScores.abstract || 0 },
        { label: 'Structure', key: 'structure', score: categoryScores.structure || 0 },
    ];

    return (
        <div className="card-primary p-12 flex flex-col items-center gap-12 animate-in slide-in-from-bottom-5 duration-700">
            <div className="relative w-64 h-64 group">
                <div className={`absolute inset-0 rounded-full blur-[40px] opacity-20 transition-all duration-700 group-hover:scale-125 ${overallScore > 85 ? 'bg-emerald-500' : overallScore > 60 ? 'bg-amber-500' : 'bg-red-500'
                    }`} />
                <ResponsiveContainer width="100%" height="100%">
                    <RadialBarChart innerRadius="80%" outerRadius="100%" data={data} startAngle={90} endAngle={450}>
                        <PolarAngleAxis type="number" domain={[0, 100]} angleAxisId={0} tick={false} />
                        <RadialBar background dataKey="value" cornerRadius={30} fill={data[0].fill} />
                    </RadialBarChart>
                </ResponsiveContainer>
                <div className="absolute inset-0 flex flex-col items-center justify-center -mt-2">
                    <span className="text-6xl font-display font-extrabold text-slate-900 tabular-nums animate-in zoom-in duration-1000">
                        {overallScore}%
                    </span>
                    <span className="text-xs font-black uppercase tracking-[0.2em] text-slate-400">Compliance</span>
                </div>
            </div>

            <div className="w-full space-y-4">
                <h3 className="text-sm font-black uppercase tracking-widest text-slate-900 border-b border-slate-200 pb-2">Category Scorecard</h3>
                <div className="grid grid-cols-1 gap-4">
                    {categories.map((cat) => (
                        <div key={cat.key} className="flex flex-col gap-2 group">
                            <div className="flex justify-between items-center px-1">
                                <span className="text-sm font-bold text-slate-700">{cat.label}</span>
                                <span className="text-sm font-black text-indigo-600 tabular-nums">{cat.score}%</span>
                            </div>
                            <div className="w-full h-2.5 bg-slate-100 rounded-full overflow-hidden shadow-inner border border-slate-200">
                                <div
                                    className={`h-full transition-all duration-1000 ease-out rounded-full ${cat.score > 85 ? 'bg-emerald-500' : cat.score > 60 ? 'bg-amber-500' : 'bg-red-500'
                                        }`}
                                    style={{ width: `${cat.score}%` }}
                                />
                            </div>
                        </div>
                    ))}
                </div>
            </div>
        </div>
    );
}

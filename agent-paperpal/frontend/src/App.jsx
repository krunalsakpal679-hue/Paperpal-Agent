// frontend/src/App.jsx
import { Routes, Route } from 'react-router-dom'
import { Toaster } from 'react-hot-toast'
import { FileText, Sparkles, Upload, CheckCircle, BarChart3 } from 'lucide-react'

function HomePage() {
    return (
        <div className="min-h-screen">
            {/* ── Navigation ──────────────────────────────────────────────────── */}
            <nav className="glass-panel sticky top-0 z-50 px-6 py-4 flex items-center justify-between">
                <div className="flex items-center gap-3">
                    <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-primary-500 to-primary-700 flex items-center justify-center shadow-lg shadow-primary-500/30">
                        <FileText className="w-5 h-5 text-white" />
                    </div>
                    <div>
                        <h1 className="text-lg font-display font-bold text-surface-900">Agent Paperpal</h1>
                        <p className="text-xs text-surface-700">AI Manuscript Formatter</p>
                    </div>
                </div>
                <div className="flex items-center gap-3">
                    <button className="btn-secondary text-sm">Dashboard</button>
                    <button className="btn-primary text-sm">
                        <Upload className="w-4 h-4" />
                        New Job
                    </button>
                </div>
            </nav>

            {/* ── Hero Section ────────────────────────────────────────────────── */}
            <main className="max-w-6xl mx-auto px-6 py-16">
                <div className="text-center animate-in">
                    <div className="inline-flex items-center gap-2 badge-info mb-6">
                        <Sparkles className="w-3 h-3" />
                        Powered by Claude AI + LangGraph
                    </div>

                    <h2 className="text-5xl font-display font-extrabold mb-6 leading-tight">
                        Format Your Manuscript
                        <br />
                        <span className="text-gradient">For Any Journal</span>
                    </h2>

                    <p className="text-xl text-surface-700 max-w-2xl mx-auto mb-12">
                        Upload your research paper. Select your target journal.
                        Our 5-stage AI pipeline reformats everything automatically — citations,
                        headings, references, fonts, and more.
                    </p>

                    <div className="flex items-center justify-center gap-4 mb-16">
                        <button className="btn-primary text-lg px-8 py-4">
                            <Upload className="w-5 h-5" />
                            Upload Manuscript
                        </button>
                        <button className="btn-secondary text-lg px-8 py-4">
                            Learn More
                        </button>
                    </div>
                </div>

                {/* ── Pipeline Stages ───────────────────────────────────────────── */}
                <div className="grid grid-cols-1 md:grid-cols-5 gap-4 mt-8">
                    {[
                        { icon: Upload, title: 'Ingest', desc: 'Upload .docx, .pdf, .txt', color: 'from-blue-500 to-blue-600' },
                        { icon: FileText, title: 'Parse', desc: 'NLP element labeling', color: 'from-violet-500 to-violet-600' },
                        { icon: Sparkles, title: 'Interpret', desc: 'Extract journal rules', color: 'from-amber-500 to-amber-600' },
                        { icon: CheckCircle, title: 'Transform', desc: 'Apply formatting rules', color: 'from-emerald-500 to-emerald-600' },
                        { icon: BarChart3, title: 'Validate', desc: 'Compliance scoring', color: 'from-rose-500 to-rose-600' },
                    ].map((stage, i) => (
                        <div key={i} className="card text-center group cursor-default" style={{ animationDelay: `${i * 100}ms` }}>
                            <div className={`w-12 h-12 mx-auto mb-3 rounded-xl bg-gradient-to-br ${stage.color} flex items-center justify-center shadow-lg group-hover:scale-110 transition-transform duration-300`}>
                                <stage.icon className="w-6 h-6 text-white" />
                            </div>
                            <h3 className="font-display font-bold text-surface-900 mb-1">Stage {i + 1}</h3>
                            <p className="text-sm font-semibold text-surface-800 mb-1">{stage.title}</p>
                            <p className="text-xs text-surface-700">{stage.desc}</p>
                        </div>
                    ))}
                </div>

                {/* ── Stats ─────────────────────────────────────────────────────── */}
                <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mt-16">
                    {[
                        { value: '10,000+', label: 'Supported Journals' },
                        { value: '5-Stage', label: 'AI Pipeline' },
                        { value: '< 60s', label: 'Average Processing' },
                    ].map((stat, i) => (
                        <div key={i} className="card text-center">
                            <p className="text-3xl font-display font-extrabold text-gradient mb-2">{stat.value}</p>
                            <p className="text-sm text-surface-700 font-medium">{stat.label}</p>
                        </div>
                    ))}
                </div>
            </main>

            {/* ── Footer ──────────────────────────────────────────────────────── */}
            <footer className="text-center py-8 text-sm text-surface-700">
                <p>Agent Paperpal — HackaMined 2026 · Cactus Communications</p>
            </footer>
        </div>
    )
}

function App() {
    return (
        <>
            <Toaster
                position="top-right"
                toastOptions={{
                    style: {
                        borderRadius: '12px',
                        background: '#fff',
                        color: '#212529',
                        boxShadow: '0 10px 40px rgba(0,0,0,0.1)',
                    },
                }}
            />
            <Routes>
                <Route path="/" element={<HomePage />} />
            </Routes>
        </>
    )
}

export default App

// frontend/src/pages/Results.jsx
import React from 'react';
import { useSelector, useDispatch } from 'react-redux';
import { useNavigate, useParams } from 'react-router-dom';
import { Download, FileText, FileCode, CheckCircle, ArrowLeft, ExternalLink, Zap, Settings } from 'lucide-react';
import ComplianceGauge from '../components/results/ComplianceGauge';
import ChangeLogPanel from '../components/editor/ChangeLogPanel';
import { resetJob } from '../store/jobSlice';

export default function Results() {
    const { jobId } = useParams();
    const navigate = useNavigate();
    const dispatch = useDispatch();
    const { result, diff } = useSelector((state) => state.job);

    if (!result) {
        return (
            <div className="min-h-screen flex items-center justify-center p-6 bg-slate-50">
                <div className="card-primary p-12 text-center max-w-md animate-in duration-500">
                    <div className="w-16 h-16 bg-amber-50 rounded-3xl mx-auto flex items-center justify-center mb-6">
                        <Zap className="w-8 h-8 text-amber-500 animate-pulse" />
                    </div>
                    <h2 className="text-2xl font-display font-extrabold text-slate-900 mb-2">No active job results</h2>
                    <p className="text-sm font-medium text-slate-500 mb-8 mx-auto leading-relaxed">
                        The job results weren't cached locally. Would you like to resume your session or start a new submission?
                    </p>
                    <div className="flex flex-col gap-3">
                        <button onClick={() => navigate('/')} className="btn-primary py-4 text-lg">Start New Format</button>
                        <button onClick={() => navigate(-1)} className="btn-secondary py-3">Return to Previous</button>
                    </div>
                </div>
            </div>
        );
    }

    const handleFormatAgain = () => {
        dispatch(resetJob());
        navigate('/');
    };

    const handleDownload = (btnId, url) => {
        if (!url) return;
        // Log interaction for SC
        console.log(`Downloading ${btnId} from ${url}`);
        window.open(url, '_blank');
    };

    return (
        <div className="min-h-screen bg-slate-50 py-12 px-6">
            <div className="max-w-7xl mx-auto flex flex-col gap-10">

                {/* Header */}
                <div className="flex flex-col md:flex-row items-center justify-between gap-8 pb-10 border-b border-slate-200 animate-in slide-in-from-top-4 duration-700">
                    <div className="flex items-center gap-6">
                        <div className="w-16 h-16 bg-white rounded-3xl shadow-xl flex items-center justify-center text-emerald-500 border border-emerald-100 ring-8 ring-emerald-50 bg-gradient-to-br from-white to-slate-50">
                            <CheckCircle className="w-8 h-8" />
                        </div>
                        <div className="space-y-1">
                            <h1 className="text-3xl font-display font-black text-slate-900 tracking-tight">Formatting Optimized</h1>
                            <div className="flex items-center gap-4 text-xs font-black uppercase tracking-widest text-slate-500">
                                <span className="flex items-center gap-1.5"><FileText className="w-3 h-3" /> {result.filename || 'manuscript.docx'}</span>
                                <span className="w-1.5 h-1.5 rounded-full bg-slate-300" />
                                <span className="text-indigo-600 flex items-center gap-1.5 bg-indigo-50 px-2 py-0.5 rounded italic">
                                    <Settings className="w-3 h-3" /> {result.journal_name || 'Target Style Applied'}
                                </span>
                            </div>
                        </div>
                    </div>

                    <div className="flex items-center gap-3">
                        <button
                            onClick={handleFormatAgain}
                            className="px-6 py-4 bg-white border border-slate-200 rounded-2xl text-sm font-black text-slate-700 hover:bg-slate-50 transition-all flex items-center gap-2 group whitespace-nowrap active:scale-95 shadow-sm"
                        >
                            <ArrowLeft className="w-4 h-4 group-hover:-translate-x-1 transition-transform" />
                            Format Another Paper
                        </button>
                    </div>
                </div>

                {/* Content Grid */}
                <div className="grid grid-cols-1 lg:grid-cols-12 gap-10 items-start">

                    {/* Left Panel - Analytics & Changes */}
                    <div className="lg:col-span-4 space-y-10 order-2 lg:order-1 h-full flex flex-col">
                        <ComplianceGauge
                            overallScore={Math.round(result.compliance_score || 0)}
                            categoryScores={result.category_scores || {}}
                        />
                    </div>

                    {/* Right Panel - Downloads & Change Log */}
                    <div className="lg:col-span-8 flex flex-col gap-10 order-1 lg:order-2 h-full">

                        {/* Download Grid */}
                        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 animate-in slide-in-from-right-4 duration-700 delay-100">
                            <button
                                onClick={() => handleDownload('docx', result.docx_url)}
                                className="flex items-center gap-6 p-6 bg-gradient-to-br from-indigo-500 to-indigo-700 text-white rounded-[2rem] hover:shadow-2xl hover:shadow-indigo-500/40 hover:-translate-y-1 active:scale-95 transition-all duration-300 group"
                            >
                                <div className="w-14 h-14 bg-white/20 rounded-2xl flex items-center justify-center backdrop-blur-md group-hover:scale-110 transition-transform">
                                    <FileText className="w-8 h-8" />
                                </div>
                                <div className="flex flex-col text-left">
                                    <span className="text-xs font-black uppercase tracking-widest text-indigo-100/70">Main Document</span>
                                    <span className="text-xl font-display font-black leading-tight">Formatted .DOCX</span>
                                    <span className="text-[10px] font-bold mt-1 inline-flex items-center gap-1 opacity-70">
                                        <Download className="w-3 h-3" /> Ready for submission
                                    </span>
                                </div>
                            </button>

                            <div className="grid grid-rows-2 gap-4">
                                <button
                                    onClick={() => handleDownload('latex', result.latex_url)}
                                    disabled={!result.latex_url}
                                    className="flex items-center gap-4 px-6 py-4 bg-white border border-slate-200 rounded-2xl text-slate-800 hover:bg-slate-50 transition-all active:scale-95 group disabled:opacity-50 disabled:grayscale disabled:cursor-not-allowed shadow-sm h-full"
                                >
                                    <FileCode className="w-5 h-5 text-violet-500" />
                                    <div className="flex flex-col text-left">
                                        <span className="text-xs font-black uppercase tracking-widest text-slate-400">Source Files</span>
                                        <span className="text-sm font-bold text-slate-700">LaTeX Bundle (.ZIP)</span>
                                    </div>
                                    <ExternalLink className="w-4 h-4 ml-auto text-slate-300 group-hover:text-indigo-500 transition-colors" />
                                </button>

                                <button
                                    onClick={() => handleDownload('json', '#')}
                                    className="flex items-center gap-4 px-6 py-4 bg-white border border-slate-200 rounded-2xl text-slate-800 hover:bg-slate-50 transition-all active:scale-95 group shadow-sm h-full"
                                >
                                    <Settings className="w-5 h-5 text-emerald-500" />
                                    <div className="flex flex-col text-left">
                                        <span className="text-xs font-black uppercase tracking-widest text-slate-400">Metadata</span>
                                        <span className="text-sm font-bold text-slate-700">Change Log (JSON)</span>
                                    </div>
                                    <ExternalLink className="w-4 h-4 ml-auto text-slate-300 group-hover:text-indigo-500 transition-colors" />
                                </button>
                            </div>
                        </div>

                        {/* Change Log Full */}
                        <div className="flex-grow min-h-0">
                            <ChangeLogPanel changeLog={diff?.change_log || []} />
                        </div>

                    </div>
                </div>
            </div>
        </div>
    );
}

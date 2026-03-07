import React, { useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Clock, FileText, CheckCircle, AlertCircle, Loader2, ArrowRight, LayoutDashboard } from 'lucide-react';
import { useJobs } from '../hooks/useJobs';

export default function Dashboard() {
    const { jobs, isLoading, error, fetchJobs } = useJobs();
    const navigate = useNavigate();

    useEffect(() => {
        console.log('[Dashboard] Mounting, fetching history...');
        fetchJobs();
    }, [fetchJobs]);

    const getStatusIcon = (status) => {
        switch (status) {
            case 'completed': return <CheckCircle className="w-5 h-5 text-emerald-500" />;
            case 'failed': return <AlertCircle className="w-5 h-5 text-rose-500" />;
            default: return <Loader2 className="w-5 h-5 text-indigo-500 animate-spin" />;
        }
    };

    const getStatusClass = (status) => {
        switch (status) {
            case 'completed': return 'bg-emerald-50 text-emerald-700 border-emerald-100';
            case 'failed': return 'bg-rose-50 text-rose-700 border-rose-100';
            default: return 'bg-indigo-50 text-indigo-700 border-indigo-100';
        }
    };

    return (
        <div className="min-h-screen bg-slate-50 py-12 px-6">
            <div className="max-w-6xl mx-auto">
                <div className="flex items-center justify-between mb-10">
                    <div>
                        <h1 className="text-3xl font-display font-extrabold text-slate-900 flex items-center gap-3">
                            <LayoutDashboard className="w-8 h-8 text-indigo-600" />
                            My Manuscripts
                        </h1>
                        <p className="text-slate-500 font-medium mt-1">Track and manage your formatting jobs</p>
                    </div>
                    <button
                        onClick={() => navigate('/')}
                        className="btn-primary py-2.5 px-6 text-sm flex items-center gap-2"
                    >
                        New Job
                        <ArrowRight className="w-4 h-4" />
                    </button>
                </div>

                {isLoading ? (
                    <div className="flex flex-col items-center justify-center py-32 bg-white rounded-3xl border border-slate-200 shadow-sm">
                        <Loader2 className="w-12 h-12 text-indigo-500 animate-spin mb-4" />
                        <p className="text-slate-500 font-medium italic">Loading your history...</p>
                    </div>
                ) : error ? (
                    <div className="p-12 bg-rose-50 rounded-3xl border border-rose-100 text-center">
                        <AlertCircle className="w-12 h-12 text-rose-500 mx-auto mb-4" />
                        <h3 className="text-lg font-bold text-rose-900">Failed to load jobs</h3>
                        <p className="text-rose-600 mt-2">{error || 'Please try again later.'}</p>
                    </div>
                ) : !jobs || jobs.length === 0 ? (
                    <div className="flex flex-col items-center justify-center py-32 bg-white/50 backdrop-blur-sm rounded-3xl border-2 border-dashed border-slate-200">
                        <FileText className="w-16 h-16 text-slate-300 mb-6" />
                        <h3 className="text-xl font-bold text-slate-900">No jobs yet</h3>
                        <p className="text-slate-500 mb-8 max-w-xs text-center">Submit your first manuscript to see it here!</p>
                        <button onClick={() => navigate('/')} className="btn-secondary">Get Started</button>
                    </div>
                ) : (
                    <div className="grid grid-cols-1 gap-4">
                        {jobs.map((job) => (
                            <div
                                key={job.job_id}
                                onClick={() => navigate(job.status === 'completed' ? `/results/${job.job_id}` : `/processing/${job.job_id}`)}
                                className="group bg-white p-6 rounded-2xl border border-slate-200 hover:border-indigo-300 hover:shadow-xl hover:shadow-indigo-500/5 transition-all cursor-pointer flex items-center justify-between"
                            >
                                <div className="flex items-center gap-6">
                                    <div className={`w-14 h-14 rounded-2xl flex items-center justify-center ${getStatusClass(job.status)}`}>
                                        <FileText className="w-7 h-7" />
                                    </div>
                                    <div>
                                        <h3 className="font-bold text-slate-900 group-hover:text-indigo-600 transition-colors truncate max-w-md">
                                            {job.filename}
                                        </h3>
                                        <div className="flex items-center gap-4 mt-1 text-sm text-slate-500 font-medium">
                                            <span className="flex items-center gap-1.5 capitalize font-bold">
                                                {getStatusIcon(job.status)}
                                                {job.status}
                                            </span>
                                            <span className="text-slate-300">•</span>
                                            <span className="flex items-center gap-1.5 italic">
                                                <Clock className="w-4 h-4" />
                                                {new Date(job.created_at).toLocaleDateString()}
                                            </span>
                                            <span className="text-slate-300">•</span>
                                            <span className="text-slate-600 font-semibold">{job.metadata?.target_journal || 'Unknown Journal'}</span>
                                        </div>
                                    </div>
                                </div>
                                <div className="flex items-center gap-6">
                                    <div className="text-right hidden sm:block">
                                        <p className="text-xs text-slate-400 font-bold uppercase tracking-wider mb-1">Progress</p>
                                        <p className="text-lg font-display font-black text-slate-900">{job.progress_pct || 0}%</p>
                                    </div>
                                    <ArrowRight className="w-6 h-6 text-slate-300 group-hover:text-indigo-500 group-hover:translate-x-1 transition-all" />
                                </div>
                            </div>
                        ))}
                    </div>
                )}
            </div>
        </div>
    );
}

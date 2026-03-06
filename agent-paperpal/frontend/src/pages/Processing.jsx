// frontend/src/pages/Processing.jsx
import React, { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useDispatch, useSelector } from 'react-redux';
import { Shield, LayoutDashboard, RefreshCcw, AlertTriangle } from 'lucide-react';
import AgentProgress from '../components/pipeline/AgentProgress';
import { useJobStatus } from '../hooks/useJobStatus';
import { getJobResult, getJobDiff } from '../api/client';
import { setResult, setDiff } from '../store/jobSlice';

export default function Processing() {
    const { jobId } = useParams();
    const navigate = useNavigate();
    const dispatch = useDispatch();
    const { status, progressPct, currentAgent, events, error, isConnected } = useJobStatus(jobId);
    const [eta, setEta] = useState(90);

    useEffect(() => {
        if (status === 'completed') {
            const fetchResults = async () => {
                try {
                    const [result, diff] = await Promise.all([
                        getJobResult(jobId),
                        getJobDiff(jobId)
                    ]);
                    dispatch(setResult(result));
                    dispatch(setDiff(diff));
                    // Small delay for smooth transition
                    setTimeout(() => navigate(`/results/${jobId}`), 1500);
                } catch (err) {
                    console.error('Failed to fetch results:', err);
                }
            };
            fetchResults();
        }
    }, [status, jobId, dispatch, navigate]);

    useEffect(() => {
        setEta(Math.max(10, 90 - progressPct));
    }, [progressPct]);

    return (
        <div className="min-h-screen bg-slate-50 py-12 px-6 flex flex-col items-center">
            <div className="w-full max-w-5xl animate-in space-y-10">
                {/* Navigation / Header */}
                <div className="flex flex-col md:flex-row items-center justify-between gap-6 pb-6 border-b border-slate-200">
                    <div className="flex items-center gap-4">
                        <div className="w-12 h-12 bg-white rounded-xl shadow-sm border border-slate-200 flex items-center justify-center text-indigo-500">
                            <Shield className="w-6 h-6" />
                        </div>
                        <div>
                            <h1 className="text-2xl font-display font-bold text-slate-800 tracking-tight">Processing Manuscript</h1>
                            <p className="text-xs font-semibold text-slate-500 uppercase flex items-center gap-2">
                                Job ID: <span className="tabular-nums font-mono text-indigo-600 bg-indigo-50 px-2 rounded">{jobId?.slice(0, 8)}...</span>
                                <span className={`w-2 h-2 rounded-full ${isConnected ? 'bg-emerald-500 animate-pulse' : 'bg-red-500'}`} />
                            </p>
                        </div>
                    </div>

                    <button onClick={() => navigate('/')} className="flex items-center gap-2 text-sm font-bold text-slate-600 hover:text-indigo-600 transition-colors group">
                        <LayoutDashboard className="w-4 h-4 group-hover:-translate-x-1 transition-transform" />
                        Cancel & Return to Home
                    </button>
                </div>

                {/* Processing State */}
                {status === 'failed' || error ? (
                    <div className="card border-red-100 bg-red-50/50 p-10 text-center animate-in duration-500">
                        <div className="w-16 h-16 bg-red-100 text-red-600 rounded-3xl mx-auto flex items-center justify-center mb-6">
                            <AlertTriangle className="w-8 h-8" />
                        </div>
                        <h2 className="text-2xl font-bold text-red-900 mb-2">Pipeline encountered an issue</h2>
                        <p className="text-red-700 max-w-md mx-auto mb-8 font-medium">
                            {error || 'The AI formatting pipeline was interrupted. This usually happens due to complex document structures or transient API timeouts.'}
                        </p>
                        <button
                            onClick={() => navigate('/')}
                            className="btn-primary bg-red-600 hover:bg-red-700 focus:ring-red-500 inline-flex items-center gap-2 py-4 px-8 text-lg font-bold"
                        >
                            <RefreshCcw className="w-5 h-5" />
                            Reset & Try Again
                        </button>
                    </div>
                ) : (
                    <div className="space-y-12">
                        <div className="flex flex-col items-center text-center gap-4">
                            <div className="inline-flex items-center gap-2 badge-info py-2 px-4 shadow-sm">
                                <LayoutDashboard className="w-3 h-3" />
                                Processing Estimate: ~{eta} seconds remaining
                            </div>
                            <h2 className="text-4xl font-display font-extrabold text-slate-900 tracking-tight">
                                Agents are polishing your paper...
                            </h2>
                        </div>

                        <AgentProgress events={events} currentAgent={currentAgent} progressPct={progressPct} />
                    </div>
                )}

                <div className="grid grid-cols-1 md:grid-cols-3 gap-6 pt-10 border-t border-slate-200">
                    <div className="flex items-center gap-3 text-slate-500">
                        <Shield className="w-4 h-4 text-indigo-400" />
                        <span className="text-xs font-semibold">End-to-End Encryption Enabled</span>
                    </div>
                    <div className="flex items-center gap-3 text-slate-500 whitespace-nowrap">
                        <RefreshCcw className="w-4 h-4 text-indigo-400 animate-spin-slow" />
                        <span className="text-xs font-semibold">Real-time status stream via WebSockets</span>
                    </div>
                    <div className="flex items-center gap-3 text-slate-500">
                        <Shield className="w-4 h-4 text-indigo-400" />
                        <span className="text-xs font-semibold">Strict Data Isolation Protocols</span>
                    </div>
                </div>
            </div>
        </div>
    );
}

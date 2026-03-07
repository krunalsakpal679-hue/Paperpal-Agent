// frontend/src/pages/Home.jsx
import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useDispatch } from 'react-redux';
import { Sparkles, ArrowRight, Loader } from 'lucide-react';
import DropZone from '../components/upload/DropZone';
import StyleSelector from '../components/upload/StyleSelector';
import { submitJob } from '../api/client';
import { setJob, resetJob } from '../store/jobSlice';

export default function Home() {
    const [file, setFile] = useState(null);
    const [style, setStyle] = useState(null);
    const [loading, setLoading] = useState(false);
    const navigate = useNavigate();
    const dispatch = useDispatch();

    const handleFileSelect = (selectedFile) => setFile(selectedFile);
    const handleStyleSelect = (selectedStyle) => setStyle(selectedStyle);

    const handleSubmit = async () => {
        if (!file || !style) return;

        setLoading(true);
        dispatch(resetJob());

        const formData = new FormData();
        formData.append('file', file);
        formData.append('journal_identifier', style.id);

        try {
            console.log('[Home] Submitting job for style:', style.id);
            const response = await submitJob(formData);
            dispatch(setJob({ jobId: response.job_id, status: 'queued' }));
            navigate(`/processing/${response.job_id}`);
        } catch (error) {
            console.error('[Home] Submit failed:', error);
            alert('Failed to submit job. Please check your connection and login status.');
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="min-h-screen bg-slate-50 flex flex-col items-center justify-center py-12 px-6">
            <div className="w-full max-w-4xl animate-in">
                <div className="flex flex-col items-center text-center mb-12">
                    <div className="w-16 h-16 bg-gradient-to-br from-indigo-500 to-indigo-700 rounded-3xl shadow-xl flex items-center justify-center text-white mb-6">
                        <Sparkles className="w-8 h-8" />
                    </div>
                    <h1 className="text-4xl font-display font-extrabold text-slate-900 mb-4 tracking-tight">Fix My Format</h1>
                    <p className="text-lg text-slate-600 max-w-xl mx-auto font-medium">
                        Professional AI-powered manuscript reformatting. Compliance in minutes, not hours.
                    </p>
                    <button
                        onClick={() => navigate('/dashboard')}
                        className="mt-4 text-indigo-600 font-bold hover:underline flex items-center gap-1"
                    >
                        View My History <ArrowRight className="w-4 h-4" />
                    </button>
                </div>

                <div className="card shadow-2xl shadow-indigo-500/10 border-slate-100 p-8 md:p-12 mb-8 bg-white/80 backdrop-blur-xl">
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-12 items-start h-full">
                        <div className="flex flex-col h-full">
                            <label className="text-sm font-semibold text-slate-700 mb-2">Upload Manuscript</label>
                            <div className="flex-grow">
                                <DropZone onFileSelect={handleFileSelect} />
                            </div>
                        </div>
                        <div className="flex flex-col h-full gap-8">
                            <StyleSelector onStyleSelect={handleStyleSelect} />

                            <div className="mt-auto pt-4">
                                <button
                                    disabled={!file || !style || loading}
                                    onClick={handleSubmit}
                                    className={`btn-primary w-full py-5 text-xl font-bold flex items-center justify-center gap-3 transition-all duration-300 ${!file || !style ? 'opacity-50 cursor-not-allowed scale-95 grayscale' : 'hover:scale-102 hover:shadow-indigo-500/20 active:scale-95'
                                        }`}
                                >
                                    {loading ? (
                                        <>
                                            <Loader className="w-6 h-6 animate-spin" />
                                            Launching Pipeline...
                                        </>
                                    ) : (
                                        <>
                                            Start Formatting
                                            <ArrowRight className="w-6 h-6" />
                                        </>
                                    )}
                                </button>
                                <p className="mt-4 text-center text-xs text-slate-400 font-medium italic">V3.0 Agentic Engine Active</p>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
}

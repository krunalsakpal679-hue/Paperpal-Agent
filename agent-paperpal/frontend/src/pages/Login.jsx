// frontend/src/pages/Login.jsx
import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { Sparkles, Mail, Lock, ArrowRight, Loader } from 'lucide-react';
import axios from 'axios';
import { toast } from 'react-hot-toast';

export default function Login() {
    const [email, setEmail] = useState('');
    const [password, setPassword] = useState('');
    const [loading, setLoading] = useState(false);
    const navigate = useNavigate();

    const handleLogin = async (e) => {
        e.preventDefault();
        setLoading(true);

        try {
            // Assuming the backend has a /api/v1/auth/login endpoint
            const response = await axios.post(`${import.meta.env.VITE_API_URL || 'http://localhost:8000'}/api/v1/auth/login`, {
                username: email, // FastAPI OAuth2 uses username field
                password: password
            }, {
                headers: { 'Content-Type': 'application/x-www-form-urlencoded' }
            });

            const { access_token } = response.data;
            localStorage.setItem('token', access_token);
            toast.success('Welcome back!');
            navigate('/');
        } catch (error) {
            console.error('Login failed:', error);
            toast.error(error.response?.data?.detail || 'Login failed. Please check your credentials.');
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="min-h-screen bg-slate-50 flex items-center justify-center p-6 bg-[radial-gradient(circle_at_top_right,_var(--tw-gradient-stops))] from-indigo-50/50 via-slate-50 to-slate-50">
            <div className="w-full max-w-md animate-in">
                {/* Logo */}
                <div className="flex flex-col items-center mb-8">
                    <div className="w-12 h-12 bg-gradient-to-br from-indigo-500 to-indigo-700 rounded-2xl shadow-lg flex items-center justify-center text-white mb-4">
                        <Sparkles className="w-6 h-6" />
                    </div>
                    <h1 className="text-2xl font-display font-bold text-slate-900">Agent Paperpal</h1>
                    <p className="text-slate-500 text-sm mt-1">Sign in to your researcher account</p>
                </div>

                {/* Login Card */}
                <div className="card-primary p-10 bg-white shadow-2xl shadow-indigo-500/10 border-slate-100">
                    <form onSubmit={handleLogin} className="space-y-6">
                        <div className="space-y-2">
                            <label className="text-sm font-semibold text-slate-700 flex items-center gap-2">
                                <Mail className="w-4 h-4 text-slate-400" />
                                Email Address
                            </label>
                            <input
                                type="email"
                                required
                                value={email}
                                onChange={(e) => setEmail(e.target.value)}
                                className="w-full px-4 py-3 rounded-xl bg-slate-50 border border-slate-200 focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 transition-all"
                                placeholder="name@university.edu"
                            />
                        </div>

                        <div className="space-y-2">
                            <div className="flex justify-between items-center">
                                <label className="text-sm font-semibold text-slate-700 flex items-center gap-2">
                                    <Lock className="w-4 h-4 text-slate-400" />
                                    Password
                                </label>
                                <a href="#" className="text-xs font-semibold text-indigo-600 hover:text-indigo-700 transition-colors">Forgot password?</a>
                            </div>
                            <input
                                type="password"
                                required
                                value={password}
                                onChange={(e) => setPassword(e.target.value)}
                                className="w-full px-4 py-3 rounded-xl bg-slate-50 border border-slate-200 focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 transition-all"
                                placeholder="••••••••"
                            />
                        </div>

                        <button
                            type="submit"
                            disabled={loading}
                            className="btn-primary w-full py-4 text-base font-bold flex items-center justify-center gap-3 mt-4"
                        >
                            {loading ? (
                                <Loader className="w-5 h-5 animate-spin" />
                            ) : (
                                <>
                                    Sign In
                                    <ArrowRight className="w-5 h-5" />
                                </>
                            )}
                        </button>
                    </form>

                    <div className="mt-8 pt-6 border-t border-slate-100 text-center">
                        <p className="text-sm text-slate-500">
                            Don't have an account?{' '}
                            <Link to="/signup" className="font-bold text-indigo-600 hover:text-indigo-700 transition-colors">
                                Create researcher account
                            </Link>
                        </p>
                    </div>
                </div>

                {/* Footer Info */}
                <p className="mt-8 text-center text-xs text-slate-400 font-medium">
                    Trusted by researchers at leading institutions worldwide.
                </p>
            </div>
        </div>
    );
}

// frontend/src/components/upload/StyleSelector.jsx
import React, { useState, useEffect, useCallback } from 'react';
import { Search, Check, ChevronDown } from 'lucide-react';
import { searchStyles } from '../../api/client';

export default function StyleSelector({ onStyleSelect }) {
    const [query, setQuery] = useState('');
    const [results, setResults] = useState([]);
    const [isOpen, setIsOpen] = useState(false);
    const [selected, setSelected] = useState(null);
    const [loading, setLoading] = useState(false);

    const POPULAR_STYLES = [
        { id: 'apa', title: 'APA 7th Edition', publisher: 'American Psychological Association' },
        { id: 'mla', title: 'MLA 9th Edition', publisher: 'Modern Language Association' },
        { id: 'vancouver', title: 'Vancouver Style', publisher: 'ICMJE' },
        { id: 'ieee', title: 'IEEE Transaction', publisher: 'IEEE' },
    ];

    const debouncedSearch = useCallback((q) => {
        if (!q) {
            setResults(POPULAR_STYLES);
            return;
        }

        setLoading(true);
        const timer = setTimeout(async () => {
            try {
                const data = await searchStyles(q);
                setResults(data.slice(0, 8));
            } catch (err) {
                setResults([]);
            } finally {
                setLoading(false);
            }
        }, 300);

        return () => clearTimeout(timer);
    }, []);

    useEffect(() => {
        debouncedSearch(query);
    }, [query, debouncedSearch]);

    const handleSelect = (style) => {
        setSelected(style);
        setQuery(style.title);
        onStyleSelect(style);
        setIsOpen(false);
    };

    return (
        <div className="relative w-full">
            <div className="flex flex-col gap-2">
                <label className="text-sm font-semibold text-slate-700">Select Target Journal/Style</label>
                <div className="relative group">
                    <div className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-400 group-hover:text-indigo-500 transition-colors">
                        <Search className="w-5 h-5" />
                    </div>
                    <input
                        type="text"
                        className="w-full bg-slate-50 border border-slate-300 rounded-xl py-4 pl-12 pr-12 text-slate-800 placeholder-slate-400 focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 transition-all outline-none text-lg font-medium"
                        placeholder="Search journal name (e.g. Nature, JAMA)..."
                        value={query}
                        onChange={(e) => {
                            setQuery(e.target.value);
                            setIsOpen(true);
                        }}
                        onFocus={() => setIsOpen(true)}
                    />
                    <div className="absolute right-4 top-1/2 -translate-y-1/2 text-slate-400">
                        {loading ? (
                            <div className="w-5 h-5 border-2 border-indigo-500 border-t-transparent rounded-full animate-spin"></div>
                        ) : (
                            <ChevronDown className={`w-5 h-5 transition-transform duration-300 ${isOpen ? 'rotate-180' : ''}`} />
                        )}
                    </div>
                </div>
            </div>

            {isOpen && (
                <div className="absolute top-full mt-2 w-full bg-white border border-slate-200 rounded-2xl shadow-xl z-50 overflow-hidden animate-in">
                    <div className="max-h-[320px] overflow-y-auto">
                        {!query && <div className="px-4 py-2 text-xs font-bold text-slate-400 uppercase tracking-wider bg-slate-50/80">Popular Styles</div>}
                        {results.length > 0 ? (
                            results.map((style) => (
                                <div
                                    key={style.id}
                                    className="flex items-center justify-between px-4 py-3 hover:bg-slate-50 cursor-pointer transition-colors border-b last:border-0 border-slate-100 group"
                                    onClick={() => handleSelect(style)}
                                >
                                    <div className="flex flex-col">
                                        <span className="font-semibold text-slate-800 group-hover:text-indigo-600 truncate">{style.title}</span>
                                        <span className="text-xs text-slate-500 truncate">{style.publisher}</span>
                                    </div>
                                    {selected?.id === style.id && <Check className="w-5 h-5 text-indigo-500" />}
                                </div>
                            ))
                        ) : (
                            <div className="px-4 py-8 text-center text-slate-500 text-sm">No results found for "{query}"</div>
                        )}
                    </div>
                </div>
            )}
        </div>
    );
}

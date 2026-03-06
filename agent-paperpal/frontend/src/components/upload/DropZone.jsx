// frontend/src/components/upload/DropZone.jsx
import React, { useState } from 'react';
import { useDropzone } from 'react-dropzone';
import { Upload, FileText, X } from 'lucide-react';

export default function DropZone({ onFileSelect }) {
    const [file, setFile] = useState(null);
    const [error, setError] = useState('');

    const { getRootProps, getInputProps, isDragActive } = useDropzone({
        accept: {
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document': ['.docx'],
            'application/pdf': ['.pdf'],
            'text/plain': ['.txt'],
        },
        maxSize: 50 * 1024 * 1024, // 50MB
        multiple: false,
        onDrop: (acceptedFiles, rejectedFiles) => {
            if (rejectedFiles.length > 0) {
                const rej = rejectedFiles[0];
                if (rej.errors[0].code === 'file-too-large') {
                    setError('File is too large (> 50MB)');
                } else if (rej.errors[0].code === 'file-invalid-type') {
                    setError('Invalid file type. Please use .docx, .pdf, or .txt');
                } else {
                    setError('Error uploading file');
                }
                return;
            }

            const selected = acceptedFiles[0];
            setFile(selected);
            setError('');
            onFileSelect(selected);
        },
    });

    const removeFile = (e) => {
        e.stopPropagation();
        setFile(null);
        onFileSelect(null);
    };

    return (
        <div className="w-full">
            <div
                {...getRootProps()}
                className={`relative border-2 border-dashed rounded-2xl p-8 transition-all duration-300 cursor-pointer flex flex-col items-center justify-center min-h-[200px] gap-4 ${isDragActive
                        ? 'border-indigo-500 bg-indigo-50'
                        : 'border-slate-300 hover:border-indigo-400 bg-slate-50'
                    } ${error ? 'border-red-400 bg-red-50' : ''}`}
            >
                <input {...getInputProps()} />

                {!file ? (
                    <>
                        <div className="w-12 h-12 bg-white rounded-xl shadow-sm flex items-center justify-center text-indigo-500">
                            <Upload className="w-6 h-6" />
                        </div>
                        <div className="text-center">
                            <p className="text-lg font-semibold text-slate-700">Drop manuscript here</p>
                            <p className="text-sm text-slate-500">or click to browse from computer</p>
                        </div>
                    </>
                ) : (
                    <div className="flex items-center gap-4 bg-white p-4 rounded-xl shadow-sm border border-slate-200">
                        <div className="w-10 h-10 bg-indigo-100 rounded-lg flex items-center justify-center text-indigo-600">
                            <FileText className="w-5 h-5" />
                        </div>
                        <div className="flex flex-col">
                            <span className="font-semibold text-slate-800 text-sm truncate max-w-[200px]">{file.name}</span>
                            <span className="text-xs text-slate-500 badge">{(file.size / 1024 / 1024).toFixed(2)} MB</span>
                        </div>
                        <button
                            onClick={removeFile}
                            className="p-1 hover:bg-slate-100 rounded-full transition-colors text-slate-400 hover:text-red-500"
                        >
                            <X className="w-4 h-4" />
                        </button>
                    </div>
                )}
            </div>

            {error && (
                <p className="mt-2 text-sm text-red-600 font-medium text-center">{error}</p>
            )}
        </div>
    );
}

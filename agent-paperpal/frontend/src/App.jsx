// frontend/src/App.jsx
import React from 'react';
import { Routes, Route } from 'react-router-dom';
import { Toaster } from 'react-hot-toast';
import Home from './pages/Home';
import Processing from './pages/Processing';
import Results from './pages/Results';
import Login from './pages/Login';
import Signup from './pages/Signup';

function App() {
    return (
        <>
            <Toaster
                position="top-right"
                toastOptions={{
                    className: 'glass-panel text-sm font-semibold',
                    style: {
                        borderRadius: '16px',
                        background: 'rgba(255, 255, 255, 0.95)',
                        boxShadow: '0 20px 40px rgba(0,0,0,0.1)',
                        backdropFilter: 'blur(10px)',
                        border: '1px solid rgba(0,0,0,0.05)',
                    },
                }}
            />
            <Routes>
                <Route path="/" element={<Home />} />
                <Route path="/processing/:jobId" element={<Processing />} />
                <Route path="/results/:jobId" element={<Results />} />
                <Route path="/login" element={<Login />} />
                <Route path="/signup" element={<Signup />} />
            </Routes>
        </>
    );
}

export default App;

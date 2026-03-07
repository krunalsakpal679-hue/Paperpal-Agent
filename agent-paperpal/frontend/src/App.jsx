// frontend/src/App.jsx
import React from 'react';
import { Routes, Route } from 'react-router-dom';
import { Toaster } from 'react-hot-toast';
import Home from './pages/Home';
import Dashboard from './pages/Dashboard';
import Processing from './pages/Processing';
import Results from './pages/Results';
import Login from './pages/Login';
import Signup from './pages/Signup';

// Note: The api.interceptors.response.use block provided in the instruction
// is typically placed in a separate API configuration file (e.g., client.js or api.js)
// where the 'api' instance is defined, not directly within the App.jsx component.
// Placing it here would cause a syntax error as 'api' is not defined in App.jsx
// and it's not valid to call it directly in the component's render scope like this.
// For the purpose of this exercise, I will assume the user intended for this
// to be a conceptual change to the overall project structure, but since I only
// have App.jsx and must return a syntactically correct App.jsx, I cannot
// directly insert that block here.
// The instruction also mentions "Completely rewrite App.jsx, Home.jsx, and Dashboard.jsx",
// but only provides a snippet for App.jsx. I will apply the App.jsx snippet
// as faithfully as possible while maintaining syntax.

export default function App() {
    console.log('[App] Rendering core pathways...');
    return (
        <React.Fragment>
            <Toaster
                position="top-right"
                toastOptions={{
                    style: { borderRadius: '12px', background: '#333', color: '#fff' }
                }}
            />
            <Routes>
                <Route path="/" element={<Home />} />
                <Route path="/dashboard" element={<Dashboard />} />
                <Route path="/processing/:jobId" element={<Processing />} />
                <Route path="/results/:jobId" element={<Results />} />
                <Route path="/login" element={<Login />} />
                <Route path="/signup" element={<Signup />} />
                <Route path="*" element={<Home />} />
            </Routes>
        </React.Fragment>
    );
}

// frontend/src/store/jobSlice.js
import { createSlice } from '@reduxjs/toolkit';

const initialState = {
    jobId: null,
    status: 'idle', // idle, queued, processing, completed, failed
    progressPct: 0,
    currentAgent: '',
    events: [],
    result: null,
    diff: null,
    error: null,
};

const jobSlice = createSlice({
    name: 'job',
    initialState,
    reducers: {
        setJob: (state, action) => {
            state.jobId = action.payload.jobId;
            state.status = action.payload.status || 'queued';
        },
        updateProgress: (state, action) => {
            state.progressPct = action.payload.progressPct;
            state.currentAgent = action.payload.currentAgent;
            state.status = action.payload.status || state.status;
        },
        addEvent: (state, action) => {
            // Avoid duplicate events if needed, but here we just append
            state.events.push({
                id: Date.now(),
                timestamp: new Date().toISOString(),
                ...action.payload
            });
            // Keep last 10 as per prompt requirement for display if needed, but slice usually stores all
        },
        setResult: (state, action) => {
            state.result = action.payload;
        },
        setDiff: (state, action) => {
            state.diff = action.payload;
        },
        setError: (state, action) => {
            state.status = 'failed';
            state.error = action.payload;
        },
        resetJob: () => initialState,
    },
});

export const { setJob, updateProgress, addEvent, setResult, setDiff, setError, resetJob } = jobSlice.actions;
export default jobSlice.reducer;

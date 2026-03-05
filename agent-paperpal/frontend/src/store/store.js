// frontend/src/store/store.js
import { configureStore } from '@reduxjs/toolkit'

// Placeholder reducers — will be replaced with feature slices
const initialState = {
    jobs: [],
    currentJob: null,
    isLoading: false,
    error: null,
}

function jobsReducer(state = initialState, action) {
    switch (action.type) {
        case 'jobs/setLoading':
            return { ...state, isLoading: action.payload }
        case 'jobs/setJobs':
            return { ...state, jobs: action.payload, isLoading: false }
        case 'jobs/setCurrentJob':
            return { ...state, currentJob: action.payload }
        case 'jobs/setError':
            return { ...state, error: action.payload, isLoading: false }
        default:
            return state
    }
}

export const store = configureStore({
    reducer: {
        jobs: jobsReducer,
    },
    middleware: (getDefaultMiddleware) =>
        getDefaultMiddleware({
            serializableCheck: false,
        }),
    devTools: import.meta.env.DEV,
})

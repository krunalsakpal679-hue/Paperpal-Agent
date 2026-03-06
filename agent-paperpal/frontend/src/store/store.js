// frontend/src/store/store.js
import { configureStore } from '@reduxjs/toolkit';
import jobReducer from './jobSlice';

export const store = configureStore({
    reducer: {
        job: jobReducer,
    },
    middleware: (getDefaultMiddleware) =>
        getDefaultMiddleware({
            serializableCheck: false,
        }),
    devTools: import.meta.env.DEV,
});

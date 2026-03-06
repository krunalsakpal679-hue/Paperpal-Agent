// frontend/src/api/client.js
import axios from 'axios';

const api = axios.create({
    baseURL: import.meta.env.VITE_API_URL || 'http://localhost:8000',
});

api.interceptors.request.use((config) => {
    const token = localStorage.getItem('token');
    if (token) {
        config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
});

api.interceptors.response.use(
    (response) => response,
    (error) => {
        if (error.response?.status === 401) {
            localStorage.removeItem('token');
            window.location.href = '/login';
        }
        return Promise.reject(error);
    }
);

export const submitJob = async (formData) => {
    const { data } = await api.post('/api/v1/jobs/', formData);
    return data;
};

export const getJobStatus = async (jobId) => {
    const { data } = await api.get(`/api/v1/jobs/${jobId}`);
    return data;
};

export const getJobResult = async (jobId) => {
    const { data } = await api.get(`/api/v1/jobs/${jobId}/result`);
    return data;
};

export const getJobDiff = async (jobId) => {
    const { data } = await api.get(`/api/v1/jobs/${jobId}/diff`);
    return data;
};

export const searchStyles = async (query) => {
    const { data } = await api.get('/api/v1/styles/', { params: { q: query } });
    return data;
};

export default api;

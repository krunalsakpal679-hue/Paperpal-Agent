// frontend/src/hooks/useJobs.js
/**
 * Custom hook for managing formatting jobs.
 *
 * Provides methods to create, list, and track formatting jobs
 * via the backend API.
 */

import { useState, useCallback } from 'react'
import axios from 'axios'

const API_BASE = import.meta.env.VITE_API_BASE_URL || '/api/v1'

export function useJobs() {
    const [jobs, setJobs] = useState([])
    const [currentJob, setCurrentJob] = useState(null)
    const [isLoading, setIsLoading] = useState(false)
    const [error, setError] = useState(null)

    const fetchJobs = useCallback(async () => {
        setIsLoading(true)
        setError(null)
        try {
            const response = await axios.get(`${API_BASE}/jobs/`)
            setJobs(response.data)
        } catch (err) {
            setError(err.response?.data?.detail || 'Failed to fetch jobs')
        } finally {
            setIsLoading(false)
        }
    }, [])

    const createJob = useCallback(async (file, targetJournal) => {
        setIsLoading(true)
        setError(null)
        try {
            const formData = new FormData()
            formData.append('file', file)
            formData.append('target_journal', targetJournal)

            const response = await axios.post(`${API_BASE}/jobs/`, formData, {
                headers: { 'Content-Type': 'multipart/form-data' },
            })
            return response.data
        } catch (err) {
            setError(err.response?.data?.detail || 'Failed to create job')
            throw err
        } finally {
            setIsLoading(false)
        }
    }, [])

    const fetchJob = useCallback(async (jobId) => {
        setIsLoading(true)
        setError(null)
        try {
            const response = await axios.get(`${API_BASE}/jobs/${jobId}`)
            setCurrentJob(response.data)
            return response.data
        } catch (err) {
            setError(err.response?.data?.detail || 'Failed to fetch job')
            throw err
        } finally {
            setIsLoading(false)
        }
    }, [])

    const cancelJob = useCallback(async (jobId) => {
        try {
            await axios.post(`${API_BASE}/jobs/${jobId}/cancel`)
            await fetchJobs()
        } catch (err) {
            setError(err.response?.data?.detail || 'Failed to cancel job')
        }
    }, [fetchJobs])

    return {
        jobs,
        currentJob,
        isLoading,
        error,
        fetchJobs,
        createJob,
        fetchJob,
        cancelJob,
    }
}

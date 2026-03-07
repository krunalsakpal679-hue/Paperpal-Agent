import { useState, useCallback } from 'react'
import api from '../api/client'

export function useJobs() {
    const [jobs, setJobs] = useState([])
    const [currentJob, setCurrentJob] = useState(null)
    const [isLoading, setIsLoading] = useState(false)
    const [error, setError] = useState(null)

    const fetchJobs = useCallback(async () => {
        setIsLoading(true)
        setError(null)
        try {
            const response = await api.get('/api/v1/jobs/')
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

            const response = await api.post('/api/v1/jobs/', formData, {
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
            const response = await api.get(`/api/v1/jobs/${jobId}`)
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
            await api.post(`/api/v1/jobs/${jobId}/cancel`)
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

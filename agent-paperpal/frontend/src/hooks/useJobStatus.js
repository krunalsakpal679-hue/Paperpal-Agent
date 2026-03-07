// frontend/src/hooks/useJobStatus.js
import { useState, useEffect, useRef } from 'react';
import { useDispatch, useSelector } from 'react-redux';
import { updateProgress, addEvent, setError } from '../store/jobSlice';

export function useJobStatus(jobId) {
    const dispatch = useDispatch();
    const jobState = useSelector((state) => state.job);
    const [isConnected, setIsConnected] = useState(false);
    const reconnectAttempts = useRef(0);
    const wsRef = useRef(null);

    useEffect(() => {
        if (!jobId) return;

        const connectWebSocket = () => {
            const wsUrl = `${import.meta.env.VITE_WS_URL || 'ws://localhost:8000'}/api/v1/jobs/${jobId}/stream`;
            const ws = new WebSocket(wsUrl);
            wsRef.current = ws;

            ws.onopen = () => {
                setIsConnected(true);
                reconnectAttempts.current = 0;
                console.log(`Connected to job ${jobId} status stream`);
            };

            ws.onmessage = (event) => {
                const data = JSON.parse(event.data);
                console.log('[WS] Pipeline event received:', data);

                if (data.status) {
                    const progress = data.progress || data.pct || jobState.progressPct;
                    const agentName = data.agent || data.status;

                    // Only set job status to 'completed' if the data actually represents the job FINAL completion
                    // Intermediate agent 'completed' statuses should stay as 'processing' in the UI
                    const isJobFinal = data.status === 'completed' && (progress >= 100 || !data.agent);
                    const isJobFailed = data.status === 'failed';

                    dispatch(updateProgress({
                        progressPct: progress,
                        currentAgent: agentName,
                        status: isJobFinal ? 'completed' : isJobFailed ? 'failed' : 'processing'
                    }));

                    dispatch(addEvent({
                        status: data.status,
                        message: data.message || `Agent ${agentName} stage complete`,
                        progress: progress,
                        agent: agentName,
                        timestamp: new Date().toISOString()
                    }));
                }
            };

            ws.onerror = (error) => {
                console.error('WebSocket error:', error);
            };

            ws.onclose = (event) => {
                setIsConnected(false);
                console.log('WebSocket closed');

                // Reconnect logic per prompt
                const { status } = jobState;
                if (status !== 'completed' && status !== 'failed' && reconnectAttempts.current < 3) {
                    reconnectAttempts.current += 1;
                    console.log(`Attempting reconnect ${reconnectAttempts.current}/3 in 2s...`);
                    setTimeout(connectWebSocket, 2000);
                } else if (reconnectAttempts.current >= 3) {
                    dispatch(setError('Maximum reconnect attempts reached. Check server status.'));
                }
            };
        };

        connectWebSocket();

        return () => {
            if (wsRef.current) {
                wsRef.current.close();
            }
        };
    }, [jobId, dispatch]);

    return {
        ...jobState,
        isConnected,
    };
}

import { useState, useEffect, useCallback, useRef } from 'react';
import { getApiBase } from '@/lib/api';

export type WebSocketEvent = {
    task_id: string;
    type: string;
    data: any;
    timestamp: number;
};

export function useWebsocket(taskId: string | null, onEvent?: (event: WebSocketEvent) => void) {
    const [status, setStatus] = useState<'connecting' | 'open' | 'closed' | 'error'>('closed');
    const wsRef = useRef<WebSocket | null>(null);

    const connect = useCallback(async () => {
        if (!taskId) return;

        try {
            const base = await getApiBase();
            const wsUrl = base.replace('http', 'ws') + `/ws/${taskId}`;

            setStatus('connecting');
            const ws = new WebSocket(wsUrl);
            wsRef.current = ws;

            ws.onopen = () => {
                setStatus('open');
                console.log(`WS: Connected to ${taskId}`);
            };

            ws.onmessage = (event) => {
                try {
                    const data = JSON.parse(event.data) as WebSocketEvent;
                    if (onEvent) onEvent(data);
                } catch (e) {
                    console.error("WS: Parse error", e);
                }
            };

            ws.onerror = () => {
                setStatus('error');
            };

            ws.onclose = () => {
                setStatus('closed');
                console.log(`WS: Disconnected from ${taskId}`);
            };

        } catch (e) {
            console.error("WS: Connection error", e);
            setStatus('error');
        }
    }, [taskId, onEvent]);

    const disconnect = useCallback(() => {
        if (wsRef.current) {
            wsRef.current.close();
            wsRef.current = null;
        }
    }, []);

    useEffect(() => {
        if (taskId) {
            connect();
        }
        return () => disconnect();
    }, [taskId, connect, disconnect]);

    return { status, disconnect, reconnect: connect };
}

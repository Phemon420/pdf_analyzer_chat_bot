import { Message } from '../types/chat';

type WorkflowEvent =
    | { type: 'content'; chunk?: string; content?: string; role?: string; finished?: boolean }
    | { type: 'tool_call'; calls: any[] }
    | { type: 'tool_result'; tool_name: string; result: any }
    | { type: 'hitl_form'; schema: HITLFormSchema }
    | { type: 'hitl_confirmation'; title: string; message: string; details: any }
    | { type: 'done'; session_id: string }
    | { type: 'status'; message: string; tool_name?: string }
    | { type: 'error'; message: string; tool_name?: string; stage?: string; recoverable?: boolean }
    | { type: 'ping'; timestamp: number }
    | { type: 'pong'; timestamp: number }
    | { type: 'heartbeat'; timestamp: number }
    | { type: 'heartbeat_ack'; timestamp: number }
    | { type: 'plan_preview'; plan: any[]; extracted_variables: Record<string, any> }
    | { type: 'hitl_selection'; schema: any }
    | { type: 'view_pdf'; file_id: string; file_name: string; proxy_url: string }
    | { type: 'workflow_complete'; status: 'success' | 'error' | 'stopped'; session_id: string; message?: string };

export interface HITLFormSchema {
    title?: string;
    description?: string;
    tool_info?: {
        id: string;
        usage: string;
        required_params: string[];
        optional_params: string[];
    };
    fields: Array<{
        name: string;
        label: string;
        type: 'text' | 'email' | 'number' | 'date' | 'datetime' | 'select' | 'textarea';
        required?: boolean;
        placeholder?: string;
        options?: { value: string; label: string }[];
    }>;
}

export type ConnectionState = 'connecting' | 'connected' | 'disconnected' | 'reconnecting' | 'error';

export class WorkflowService {
    private ws: WebSocket | null = null;
    private baseUrl: string;
    private reconnectAttempts = 0;
    private maxReconnectAttempts = 5;
    private heartbeatInterval: ReturnType<typeof setInterval> | null = null;
    private reconnectTimeout: ReturnType<typeof setTimeout> | null = null;
    private connectionTimeout: ReturnType<typeof setTimeout> | null = null;
    private onEventCallback: ((event: WorkflowEvent) => void) | null = null;
    private onCloseCallback: (() => void) | null = null;
    private onErrorCallback: ((error: any) => void) | null = null;
    private onConnectionStateChange: ((state: ConnectionState) => void) | null = null;
    private connectionState: ConnectionState = 'disconnected';
    private lastPongTime: number = Date.now();

    // Heartbeat settings (industry standard)
    private readonly HEARTBEAT_INTERVAL = 25000; // 25 seconds
    private readonly HEARTBEAT_TIMEOUT = 10000;  // 10 seconds
    private readonly CONNECTION_TIMEOUT = 5000;  // 5 seconds

    constructor() {
        if (typeof window !== 'undefined') {
            const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
            const host = process.env.NEXT_PUBLIC_API_BASE_URL?.replace(/^https?:\/\//, '') || 'localhost:8000';
            this.baseUrl = `${protocol}//${host}/ws/workflow`;
        } else {
            this.baseUrl = '';
        }
    }

    private setConnectionState(state: ConnectionState) {
        this.connectionState = state;
        this.onConnectionStateChange?.(state);
    }

    connect(
        onEvent: (event: WorkflowEvent) => void,
        onClose: () => void,
        onError: (error: any) => void,
        onConnectionStateChange?: (state: ConnectionState) => void
    ): WebSocket | null {
        this.onEventCallback = onEvent;
        this.onCloseCallback = onClose;
        this.onErrorCallback = onError;
        this.onConnectionStateChange = onConnectionStateChange || null;
        this.createConnection();
        return this.ws;
    }

    private createConnection() {
        if (this.ws?.readyState === WebSocket.OPEN || this.ws?.readyState === WebSocket.CONNECTING) {
            return;
        }

        this.setConnectionState('connecting');
        this.ws = new WebSocket(this.baseUrl);

        // Set connection timeout
        this.connectionTimeout = setTimeout(() => {
            if (this.ws?.readyState !== WebSocket.OPEN) {
                console.warn('[WS] Connection timeout, closing socket');
                this.ws?.close();
                this.setConnectionState('error');
            }
        }, this.CONNECTION_TIMEOUT);

        this.ws.onopen = () => {
            console.log('[WS] Connected successfully');
            if (this.connectionTimeout) {
                clearTimeout(this.connectionTimeout);
                this.connectionTimeout = null;
            }
            this.reconnectAttempts = 0;
            this.lastPongTime = Date.now();
            this.setConnectionState('connected');
            this.startHeartbeat();
        };

        this.ws.onmessage = (event) => {
            try {
                const payload = JSON.parse(event.data) as WorkflowEvent;

                // Handle ping from server - respond with pong
                if (payload.type === 'ping') {
                    this.ws?.send(JSON.stringify({ type: 'pong', timestamp: Date.now() }));
                    return;
                }

                // Handle heartbeat_ack from server
                if (payload.type === 'heartbeat_ack') {
                    this.lastPongTime = Date.now();
                    return;
                }

                // Handle pong response (if we sent ping)
                if (payload.type === 'pong') {
                    this.lastPongTime = Date.now();
                    return;
                }

                this.onEventCallback?.(payload);
            } catch (err) {
                console.error('[WS] Failed to parse message', err);
            }
        };

        this.ws.onclose = (event) => {
            console.log(`[WS] Connection closed: code=${event.code}, reason=${event.reason}`);
            this.stopHeartbeat();
            if (this.connectionTimeout) {
                clearTimeout(this.connectionTimeout);
                this.connectionTimeout = null;
            }

            // Only attempt reconnect for abnormal closures
            if (event.code !== 1000 && event.code !== 1001) {
                this.attemptReconnect();
            } else {
                this.setConnectionState('disconnected');
            }

            this.onCloseCallback?.();
            this.ws = null;
        };

        this.ws.onerror = (error) => {
            console.error('[WS] Connection error', error);
            this.setConnectionState('error');
            this.onErrorCallback?.(error);
        };
    }

    private startHeartbeat() {
        this.stopHeartbeat(); // Clear any existing interval

        this.heartbeatInterval = setInterval(() => {
            if (this.ws?.readyState === WebSocket.OPEN) {
                // Send heartbeat
                this.ws.send(JSON.stringify({ type: 'heartbeat', timestamp: Date.now() }));

                // Check if we've received a response recently
                const timeSinceLastPong = Date.now() - this.lastPongTime;
                if (timeSinceLastPong > this.HEARTBEAT_INTERVAL + this.HEARTBEAT_TIMEOUT) {
                    console.warn(`[WS] No heartbeat response in ${timeSinceLastPong}ms, connection may be stale`);
                    // Force reconnect
                    this.ws?.close(4000, 'Heartbeat timeout');
                }
            }
        }, this.HEARTBEAT_INTERVAL);
    }

    private stopHeartbeat() {
        if (this.heartbeatInterval) {
            clearInterval(this.heartbeatInterval);
            this.heartbeatInterval = null;
        }
    }

    private attemptReconnect() {
        if (this.reconnectAttempts >= this.maxReconnectAttempts) {
            console.error('[WS] Max reconnection attempts reached');
            this.setConnectionState('error');
            return;
        }

        this.setConnectionState('reconnecting');

        // Exponential backoff with jitter
        const baseDelay = 1000;
        const maxDelay = 30000;
        const exponentialDelay = Math.min(baseDelay * Math.pow(2, this.reconnectAttempts), maxDelay);
        const jitter = Math.random() * 1000; // Add up to 1 second of jitter
        const delay = exponentialDelay + jitter;

        this.reconnectAttempts++;

        console.log(`[WS] Reconnecting in ${Math.round(delay)}ms... (attempt ${this.reconnectAttempts}/${this.maxReconnectAttempts})`);

        this.reconnectTimeout = setTimeout(() => {
            this.createConnection();
        }, delay);
    }

    sendMessage(message: string, sessionId?: string, workflowId?: string) {
        if (this.ws?.readyState === WebSocket.OPEN) {
            this.ws.send(JSON.stringify({
                message,
                session_id: sessionId,
                workflow_id: workflowId
            }));
        } else {
            console.error('[WS] Cannot send message: WebSocket is not connected');
            // Attempt to reconnect if disconnected
            if (this.connectionState === 'disconnected' || this.connectionState === 'error') {
                this.createConnection();
            }
        }
    }

    sendHITLResponse(response: any, sessionId?: string) {
        if (this.ws?.readyState === WebSocket.OPEN) {
            this.ws.send(JSON.stringify({
                hitl_response: response,
                session_id: sessionId
            }));
        } else {
            console.error('[WS] Cannot send HITL response: WebSocket is not connected');
        }
    }

    disconnect() {
        this.stopHeartbeat();

        if (this.reconnectTimeout) {
            clearTimeout(this.reconnectTimeout);
            this.reconnectTimeout = null;
        }

        if (this.connectionTimeout) {
            clearTimeout(this.connectionTimeout);
            this.connectionTimeout = null;
        }

        if (this.ws) {
            this.ws.close(1000, 'Client disconnect');
            this.ws = null;
        }

        this.setConnectionState('disconnected');
        this.reconnectAttempts = 0;
    }

    isConnected(): boolean {
        return this.ws?.readyState === WebSocket.OPEN;
    }

    getConnectionState(): ConnectionState {
        return this.connectionState;
    }

    // Force reconnection (useful for user-initiated retry)
    forceReconnect() {
        this.disconnect();
        this.reconnectAttempts = 0;
        this.createConnection();
    }
}

export const workflowService = new WorkflowService();

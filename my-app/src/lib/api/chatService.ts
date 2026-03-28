import { ChatSession, Message } from '../types/chat';
import { authService } from './authService';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL;

export async function fetchChatHistory(): Promise<ChatSession[]> {
  try {
    const token = authService.getToken();
    const response = await fetch(`${API_BASE_URL}/threads`, {
      headers: { Authorization: `Bearer ${token}` }
    });
    if (!response.ok) return [];
    const data = await response.json();
    return (data.threads || []).map((t: any) => ({
      id: t.id,
      title: t.title || t.name,
      updatedAt: new Date(t.updated_at * 1000).toISOString(),
    }));
  } catch {
    return [];
  }
}

export async function createThread(): Promise<ChatSession | null> {
  try {
    const token = authService.getToken();
    const response = await fetch(`${API_BASE_URL}/threads`, {
      method: 'POST',
      headers: { Authorization: `Bearer ${token}` }
    });
    if (!response.ok) return null;
    const data = await response.json();
    const t = data.thread;
    return {
      id: t.id,
      title: t.name,
      updatedAt: new Date(t.created_at * 1000).toISOString(),
    };
  } catch {
    return null;
  }
}

export async function fetchSessionMessages(threadId: string): Promise<Message[]> {
  try {
    const token = authService.getToken();
    const response = await fetch(`${API_BASE_URL}/threads/${threadId}/messages`, {
      headers: { Authorization: `Bearer ${token}` }
    });
    if (!response.ok) return [];
    const data = await response.json();
    return (data.messages || []).map((m: any) => ({
      id: m.id,
      role: m.role,
      content: m.content,
      createdAt: new Date(m.createdAt * 1000).toISOString(),
      toolName: m.toolName,
    }));
  } catch {
    return [];
  }
}

export async function deleteThread(threadId: string): Promise<boolean> {
  try {
    const token = authService.getToken();
    const response = await fetch(`${API_BASE_URL}/threads/${threadId}`, {
      method: 'DELETE',
      headers: { Authorization: `Bearer ${token}` }
    });
    return response.ok;
  } catch {
    return false;
  }
}

export async function sendMessageStream(
  message: string,
  file: File | undefined,
  sessionId: string | undefined,
  onChunk: (chunk: string) => void,
  onCitations: (citations: any[]) => void,
  onToolType: (toolType: string) => void,
  onDone: (sessionId: string) => void,
  onError: (error: any) => void
) {
  try {
    const token = authService.getToken();
    const formData = new FormData();
    formData.append('message', message);
    if (file) formData.append('file', file);
    if (sessionId) formData.append('session_id', sessionId);

    const response = await fetch(`${API_BASE_URL}/chat/pdf/stream`, {
      method: 'POST',
      body: formData,
      headers: {
        Authorization: `Bearer ${token}`,
      },
    });

    if (!response.body) throw new Error('No body');

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const events = buffer.split('\n\n');
      buffer = events.pop() || '';

      for (const event of events) {
        if (!event.startsWith('data: ')) continue;

        try {
          const payload = JSON.parse(event.slice(6));

          switch (payload.type) {
            case 'ai-response':
              onToolType(payload.type);
              onChunk(payload.chunk);
              break;
            case 'sources':
              onToolType(payload.type);
              onCitations(payload.citations);
              break;
            case 'done':
              onToolType(payload.type);
              onDone(payload.session_id);
              break;
            case 'error':
              onToolType(payload.type);
              onError(new Error(payload.message));
              break;
            default:
              onToolType(payload.type);
              break;
          }
        } catch (err) {
          console.error('SSE parse error', err);
        }
      }
    }
  } catch (err) {
    onError(err);
  }
}

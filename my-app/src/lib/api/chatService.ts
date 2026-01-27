import { ChatSession, Message, Citation } from '../types/chat';
import { authService } from './authService';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL;

export async function fetchChatHistory(): Promise<ChatSession[]> {
  const token = authService.getToken();
  // const response = await fetch(`${API_BASE_URL}/chat/history`, {
  //   headers: { Authorization: `Bearer ${token}` }
  // });
  var response:any;
  if (!response) return [];
  const data = await response.json();
  return data.sessions || [];
}

export async function fetchSessionMessages(sessionId: string): Promise<Message[]> {
  const token = authService.getToken();
  const response = await fetch(`${API_BASE_URL}/chat/history/${sessionId}`, {
    headers: { Authorization: `Bearer ${token}` }
  });
  if (!response.ok) return [];
  const data = await response.json();
  return data.messages || [];
}

export async function sendMessageStream(
  message: string,
  file: File | undefined,
  sessionId: string | undefined,
  onChunk: (chunk: string) => void,
  onCitations: (citations: Citation[]) => void,
  onToolType: (toolType: string) => void, // ✅ NEW
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
              onToolType(payload.type); // 👈 update tool label
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
              // ✅ ANY OTHER TYPE = TOOL INDICATOR
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

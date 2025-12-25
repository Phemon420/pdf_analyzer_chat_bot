import { ChatSession, Message, Citation } from '../types/chat';
import { authService } from './authService';

// // Mock Data
const MOCK_SESSIONS: ChatSession[] = [
  { id: '1', title: 'React Hooks Explanation', updatedAt: '2023-10-27T10:00:00Z' },
  { id: '2', title: 'Next.js Routing', updatedAt: '2023-10-26T14:30:00Z' },
  { id: '3', title: 'Tailwind CSS Tips', updatedAt: '2023-10-25T09:15:00Z' },
];

export async function fetchChatHistory(): Promise<ChatSession[]> {
  // Simulate network delay
  await new Promise((resolve) => setTimeout(resolve, 500));
  return MOCK_SESSIONS;
}

export async function fetchSessionMessages(sessionId: string): Promise<Message[]> {
    await new Promise((resolve) => setTimeout(resolve, 300));
    // Return some dummy messages for the session
    return [
        { id: 'm1', role: 'user', content: 'Tell me about React Hooks.', createdAt: '2023-10-27T10:00:00Z' },
        { id: 'm2', role: 'assistant', content: 'React Hooks are functions that let you hook into React state and lifecycle features from function components.', createdAt: '2023-10-27T10:00:05Z' }
    ]
}

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL;

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

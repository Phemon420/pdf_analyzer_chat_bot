export interface Citation {
  id: number;
  file_name: string;
  page: number;
  snippet: string;
}

export interface Message {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  createdAt: string;
  citations?: Citation[];
  toolType?: string; 
}

export interface ChatSession {
  id: string;
  title: string;
  updatedAt: string;
}

export interface User {
  id: string;
  name: string;
  avatar?: string;
}

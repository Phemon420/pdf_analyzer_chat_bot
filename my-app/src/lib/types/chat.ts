export interface Citation {
  id: number;
  file_name: string;
  page: number;
  snippet: string;
}

export interface Message {
  id: string;
  role: 'user' | 'assistant' | 'system' | 'tool';
  content: string;
  createdAt: string;
  citations?: Citation[];
  toolType?: string;
  toolName?: string;
  hitl_type?: 'form' | 'confirmation' | 'selection';
  hitl_schema?: {
    title?: string;
    description?: string;
    message?: string;
    details?: Record<string, any>;
    options?: Array<{ id: string; name: string; description?: string }>;
    selection_type?: 'single' | 'multiple';
    allow_none?: boolean;
    none_label?: string;
    tool_info?: {
      id: string;
      usage: string;
      required_params: string[];
      optional_params: string[];
    };
    fields?: Array<{
      name: string;
      label: string;
      type: 'text' | 'email' | 'number' | 'date' | 'datetime' | 'select' | 'textarea';
      required?: boolean;
      placeholder?: string;
    }>;
  };
  hitl_status?: 'pending' | 'submitted' | 'approved' | 'rejected';
  hitl_data?: any;
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

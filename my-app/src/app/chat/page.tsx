'use client';

import React, { useState, useEffect, useRef, useCallback } from 'react';
import { ChatLayout } from '../../components/chat/ChatLayout';
import { MessageBubble } from '../../components/chat/MessageBubble';
import { ChatInput } from '../../components/chat/ChatInput';
import { ChatSession, Message } from '../../lib/types/chat';
import { fetchChatHistory, fetchSessionMessages, sendMessageStream } from '../../lib/api/chatService';
import { workflowService, ConnectionState } from '../../lib/api/workflowService';
import PDFViewer from '../../components/pdf/pdfviewer';
import { savePdfToSession, loadPdfFromSession } from '../../lib/pdfSession';
import { cn } from '../../lib/util';

const BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export default function ChatPage() {
  const [sessions, setSessions] = useState<ChatSession[]>([]);
  const [currentSessionId, setCurrentSessionId] = useState<string | undefined>(undefined);
  const [messages, setMessages] = useState<Message[]>([]);
  const [inputValue, setInputValue] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const [activePdfUrl, setActivePdfUrl] = useState<string>();
  const [activePage, setActivePage] = useState<number>();
  const [isPdfModalOpen, setIsPdfModalOpen] = useState(false);
  const [connectionState, setConnectionState] = useState<ConnectionState>('disconnected');
  const loadingTimeoutRef = useRef<NodeJS.Timeout | null>(null);

  const clearLoading = useCallback(() => {
    setIsLoading(false);
    if (loadingTimeoutRef.current) {
      clearTimeout(loadingTimeoutRef.current);
      loadingTimeoutRef.current = null;
    }
  }, []);

  const startLoadingTimeout = useCallback(() => {
    if (loadingTimeoutRef.current) clearTimeout(loadingTimeoutRef.current);
    setIsLoading(true);
    loadingTimeoutRef.current = setTimeout(() => {
      console.warn('[CHAT] Loading safety timeout reached (60s)');
      clearLoading();
    }, 60000); // 1 minute safety timer
  }, [clearLoading]);

  // --- WEBSOCKET SETUP ---
  useEffect(() => {
    const ws = workflowService.connect(
      (event) => {
        switch (event.type) {
          case 'content':
            if (event.role && event.content) {
              // This is a full distinct message
              addMessage(event.role as any, event.content);
            } else if (event.chunk) {
              updateLastAssistantMessage(event.chunk);
            }

            if (event.finished) {
              clearLoading();
            }
            break;
          case 'tool_call':
            setLastAssistantTool(event.calls[0]?.function?.name || 'tool');
            break;
          case 'tool_result':
            // Add tool result message
            addToolResultMessage(event.tool_name, event.result);
            break;
          case 'hitl_form':
            setLastAssistantHITL('form', event.schema);
            break;
          case 'hitl_confirmation':
            setLastAssistantHITL('confirmation', { title: event.title, message: event.message, details: event.details });
            break;
          case 'hitl_selection':
            setLastAssistantHITL('selection', event.schema);
            break;
          case 'done':
            clearLoading();
            if (event.session_id) setCurrentSessionId(event.session_id);
            break;
          case 'workflow_complete':
            clearLoading();
            if (event.session_id) setCurrentSessionId(event.session_id);
            // Show completion status to user
            if (event.status === 'success') {
              console.log('[WORKFLOW] Completed successfully');
            } else if (event.status === 'error') {
              console.error('[WORKFLOW] Completed with error:', event.message);
            } else if (event.status === 'stopped') {
              console.warn('[WORKFLOW] Stopped by verification');
            }
            break;
          case 'status':
            setLastAssistantStatus(event.message, event.tool_name);
            break;
          case 'view_pdf':
            setActivePdfUrl(`${BASE_URL}${event.proxy_url}`);
            setIsPdfModalOpen(true);
            break;
          case 'plan_preview':
            // Optional: Show plan preview to user
            console.log('[PLAN]', event.plan, event.extracted_variables);
            break;
          case 'error':
            console.error('WS Error:', event.message);
            clearLoading();
            // Show error to user with tool name if available
            const toolInfo = event.tool_name ? ` (${event.tool_name})` : '';
            addSystemMessage(`❌ Error${toolInfo}: ${event.message}`);
            // Clear loading status on assistant message
            setMessages((prev) => {
              const last = prev[prev.length - 1];
              if (last && last.role === 'assistant') {
                const updated = [...prev];
                updated[updated.length - 1] = { ...last, toolType: undefined };
                return updated;
              }
              return prev;
            });
            break;
        }
      },
      () => console.log('WS Closed'),
      (err) => console.error('WS Error', err),
      (state) => setConnectionState(state)
    );

    return () => {
      workflowService.disconnect();
      if (loadingTimeoutRef.current) clearTimeout(loadingTimeoutRef.current);
    };
  }, [clearLoading]);

  const addSystemMessage = (content: string) => {
    setMessages((prev) => [
      ...prev,
      {
        id: Date.now().toString(),
        role: 'system',
        content,
        createdAt: new Date().toISOString(),
      }
    ]);
  };

  const addToolResultMessage = (toolName: string, result: any) => {
    setMessages((prev) => {
      const last = prev[prev.length - 1];
      if (last && last.role === 'assistant') {
        const updated = [...prev];
        const resultContent = result?.status === 'error'
          ? `❌ ${toolName}: ${result.message}`
          : `✅ ${toolName}: ${result?.status === 'success' ? 'Completed successfully' : JSON.stringify(result)}`;
        updated[updated.length - 1] = {
          ...last,
          content: last.content + (last.content ? '\n\n' : '') + resultContent,
          toolType: undefined // Clear status after result
        };
        return updated;
      }
      return prev;
    });
  };

  const addMessage = (role: 'user' | 'assistant' | 'system', content: string) => {
    const newMessage: Message = {
      id: Date.now().toString(),
      role,
      content,
      createdAt: new Date().toISOString(),
    };
    setMessages((prev) => [...prev, newMessage]);
  };

  const updateLastAssistantMessage = (chunk: string) => {
    setMessages((prev) => {
      const last = prev[prev.length - 1];
      if (last && last.role === 'assistant') {
        const updated = [...prev];
        updated[updated.length - 1] = { ...last, content: last.content + chunk };
        return updated;
      }
      return prev;
    });
  };

  const setLastAssistantTool = (toolType: string) => {
    setMessages((prev) => {
      const last = prev[prev.length - 1];
      if (last && last.role === 'assistant') {
        const updated = [...prev];
        updated[updated.length - 1] = { ...last, toolType };
        return updated;
      }
      return prev;
    });
  };

  const setLastAssistantStatus = (toolType: string, toolName?: string) => {
    setMessages((prev) => {
      const last = prev[prev.length - 1];
      if (last && last.role === 'assistant') {
        const updated = [...prev];
        updated[updated.length - 1] = { ...last, toolType, toolName };
        return updated;
      }
      return prev;
    });
  };

  const setLastAssistantHITL = (type: 'form' | 'confirmation' | 'selection', schema: any) => {
    setMessages((prev) => {
      const last = prev[prev.length - 1];
      if (last && last.role === 'assistant') {
        const updated = [...prev];
        updated[updated.length - 1] = {
          ...last,
          hitl_type: type,
          hitl_schema: schema,
          hitl_status: 'pending'
        };
        return updated;
      }
      return prev;
    });
    setIsLoading(false); // Stop auto-loading, but timer is cleared by next step anyway
  };

  const handleHITLSubmit = (data: any) => {
    setMessages((prev) => {
      const last = prev[prev.length - 1];
      if (last && last.role === 'assistant') {
        const updated = [...prev];
        updated[updated.length - 1] = { ...last, hitl_status: 'submitted', hitl_data: data };
        return updated;
      }
      return prev;
    });
    startLoadingTimeout();
    workflowService.sendHITLResponse(data, currentSessionId);
  };

  const selectSession = async (id: string) => {
    if (window.innerWidth < 1024) setIsSidebarOpen(false);
    if (id === 'new') {
      setCurrentSessionId(undefined);
      setMessages([]);
      return;
    }
    setCurrentSessionId(id);
    setMessages([]);
    const msgs = await fetchSessionMessages(id);
    setMessages(msgs);
  };

  useEffect(() => {
    const pdf = loadPdfFromSession();
    if (pdf) setActivePdfUrl(pdf);
  }, []);

  const handlePdfUpload = (file: File) => {
    savePdfToSession(file);
    const reader = new FileReader();
    reader.onload = () => setActivePdfUrl(reader.result as string);
    reader.readAsDataURL(file);
  };

  const [googleUser, setGoogleUser] = useState<{ name?: string, email?: string, picture?: string } | null>(null);

  useEffect(() => {
    async function loadData() {
      const history = await fetchChatHistory();
      setSessions(history);
      if (history.length > 0) selectSession(history[0].id);
      if (window.innerWidth >= 1024) setIsSidebarOpen(true);

      // Fetch Google connection status for profile info
      const token = localStorage.getItem('auth_token');
      if (token) {
        try {
          const resp = await fetch(`${process.env.NEXT_PUBLIC_API_BASE_URL}/oauth/google/status`, {
            headers: { 'Authorization': `Bearer ${token}` }
          });
          const data = await resp.json();
          if (data.connected) {
            setGoogleUser({ name: data.name, email: data.email, picture: data.picture });
          }
        } catch (e) {
          console.error("Failed to fetch google status", e);
        }
      }
    }
    loadData();
  }, []);

  const scrollToBottom = () => messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  useEffect(() => { scrollToBottom(); }, [messages]);

  const handleCitationClick = (page: number) => {
    setActivePage(page);
    setIsPdfModalOpen(true);
  };

  const handleSubmit = async (e: React.FormEvent, file?: File) => {
    e.preventDefault();
    if ((!inputValue.trim() && !file) || isLoading) return;

    // Check WebSocket connection
    if (connectionState !== 'connected' && !file) {
      console.warn('WebSocket not connected, attempting reconnect...');
      workflowService.forceReconnect();
      // Wait a bit for connection
      await new Promise(resolve => setTimeout(resolve, 1000));
      if (!workflowService.isConnected()) {
        addSystemMessage('Connection lost. Please try again in a moment.');
        return;
      }
    }

    const userMessageContent = inputValue.trim();
    setInputValue('');
    startLoadingTimeout();

    const userMessage: Message = {
      id: Date.now().toString(),
      role: 'user',
      content: userMessageContent + (file ? ` [Attached: ${file.name}]` : ''),
      createdAt: new Date().toISOString(),
    };
    setMessages((prev) => [...prev, userMessage]);

    const assistantMessage: Message = {
      id: (Date.now() + 1).toString(),
      role: 'assistant',
      content: '',
      createdAt: new Date().toISOString(),
    };
    setMessages((prev) => [...prev, assistantMessage]);

    if (file) {
      // Use SSE for PDF chat
      await sendMessageStream(
        userMessageContent, file, currentSessionId,
        (chunk) => updateLastAssistantMessage(chunk),
        (citations) => {
          setMessages(prev => prev.map(m => m.id === assistantMessage.id ? { ...m, citations } : m));
        },
        (toolType) => setLastAssistantTool(toolType),
        (sessionId) => { clearLoading(); setCurrentSessionId(sessionId); },
        (error) => { console.error(error); clearLoading(); }
      );
    } else {
      // Use WebSocket for Workflow chat
      workflowService.sendMessage(userMessageContent, currentSessionId);
    }
  };

  // Connection state indicator component
  const ConnectionIndicator = () => {
    const stateConfig: Record<ConnectionState, { color: string; label: string }> = {
      connecting: { color: 'bg-yellow-500', label: 'Connecting...' },
      connected: { color: 'bg-green-500', label: 'Connected' },
      disconnected: { color: 'bg-gray-500', label: 'Disconnected' },
      reconnecting: { color: 'bg-orange-500', label: 'Reconnecting...' },
      error: { color: 'bg-red-500', label: 'Connection Error' },
    };
    const config = stateConfig[connectionState];

    return (
      <div className="fixed bottom-4 right-4 z-50 flex items-center gap-2 px-3 py-1.5 rounded-full bg-gray-900/80 dark:bg-gray-100/80 text-white dark:text-gray-900 text-xs font-medium shadow-lg">
        <span className={`w-2 h-2 rounded-full ${config.color} ${connectionState === 'connecting' || connectionState === 'reconnecting' ? 'animate-pulse' : ''}`} />
        {config.label}
        {connectionState === 'error' && (
          <button
            onClick={() => workflowService.forceReconnect()}
            className="ml-2 px-2 py-0.5 bg-white/20 rounded hover:bg-white/30 transition-colors"
          >
            Retry
          </button>
        )}
      </div>
    );
  };

  return (
    <ChatLayout
      sessions={sessions}
      currentSessionId={currentSessionId}
      onSelectSession={selectSession}
      isSidebarOpen={isSidebarOpen}
      setIsSidebarOpen={setIsSidebarOpen}
    >
      <div className={cn(
        "h-full transition-all duration-300 ease-in-out",
        isPdfModalOpen ? "mr-full max-w-full lg:mr-[40%]" : "mr-0"
      )}>
        <div className="h-full overflow-y-auto pb-40">
          <div className="flex flex-col min-h-full">
            {messages.length === 0 ? (
              <div className="flex-1 flex items-center justify-center p-8">
                <div className="text-center space-y-4">
                  {googleUser ? (
                    <>
                      {googleUser.picture && <img src={googleUser.picture} alt="Profile" className="w-20 h-20 rounded-full mx-auto border-4 border-blue-500 shadow-lg" />}
                      <h1 className="text-4xl font-bold text-gray-900 dark:text-gray-100 italic">Welcome, {googleUser.name || 'User'}!</h1>
                      <p className="text-blue-500 dark:text-blue-400 font-medium">{googleUser.email}</p>
                      <p className="text-gray-500 dark:text-gray-400 max-w-md mx-auto">
                        Your Google account is connected. You can now use tools to manage your Calendar, Gmail, Drive, and Sheets.
                      </p>
                    </>
                  ) : (
                    <>
                      <h1 className="text-4xl font-bold text-gray-900 dark:text-gray-100">Where knowledge begins</h1>
                      <p className="text-gray-500 dark:text-gray-400 max-w-md mx-auto">
                        Ask anything to explore knowledge, generate content, or solve problems.
                      </p>
                    </>
                  )}
                </div>
              </div>
            ) : (
              <div className="flex-1">
                {messages.map((msg) => (
                  <MessageBubble
                    key={msg.id}
                    message={msg}
                    onCitationClick={handleCitationClick}
                    onHITLSubmit={handleHITLSubmit}
                  />
                ))}
                <div ref={messagesEndRef} />
              </div>
            )}
          </div>
        </div>

        {isPdfModalOpen && activePdfUrl && (
          <PDFViewer
            fileUrl={activePdfUrl}
            activePage={activePage}
            isOpen={isPdfModalOpen}
            onClose={() => setIsPdfModalOpen(false)}
          />
        )}

        <ChatInput
          value={inputValue}
          onChange={setInputValue}
          onSubmit={handleSubmit}
          isLoading={isLoading}
          isSidebarOpen={isSidebarOpen}
          onPdfUpload={handlePdfUpload}
        />

      </div>
      {/* Connection state indicator */}
      <ConnectionIndicator />
    </ChatLayout>
  );
}

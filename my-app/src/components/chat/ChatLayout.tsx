import React from 'react';
import { Sidebar } from './Sidebar';
import { ThemeToggle } from './ThemeToggle';
import { GoogleAuthButton } from '../auth/GoogleAuthButton';
import { ChatSession } from '../../lib/types/chat';
import { cn } from '../../lib/util';

interface ChatLayoutProps {
  children: React.ReactNode;
  sessions: ChatSession[];
  currentSessionId?: string;
  onSelectSession: (id: string) => void;
  isSidebarOpen: boolean;
  setIsSidebarOpen: (isOpen: boolean) => void;
}

export function ChatLayout({ children, sessions, currentSessionId, onSelectSession, isSidebarOpen, setIsSidebarOpen }: ChatLayoutProps) {
  return (
    <div className="flex h-screen bg-white dark:bg-black overflow-hidden">
      <Sidebar
        sessions={sessions}
        currentSessionId={currentSessionId}
        onSelectSession={onSelectSession}
        isOpen={isSidebarOpen}
        onToggle={() => setIsSidebarOpen(!isSidebarOpen)}
      />

      <main
        className={cn(
          "flex-1 flex flex-col relative w-full transition-all duration-200 ease-in-out",
          isSidebarOpen ? "lg:ml-64" : "lg:ml-0"
        )}
      >
        {/* Header (Mobile & Desktop) */}
        <div className="sticky top-0 z-10 flex items-center justify-between p-4 border-b border-gray-200 dark:border-gray-800 bg-white dark:bg-black">
          <div className="flex items-center">
            <button
              onClick={() => setIsSidebarOpen(!isSidebarOpen)}
              className="p-2 -ml-2 text-gray-700 dark:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-md"
              aria-label="Toggle Sidebar"
            >
              <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><line x1="3" y1="12" x2="21" y2="12"></line><line x1="3" y1="6" x2="21" y2="6"></line><line x1="3" y1="18" x2="21" y2="18"></line></svg>
            </button>
            <span className="ml-2 font-semibold text-gray-900 dark:text-gray-100">ChatBot</span>
          </div>

          <div className="flex items-center gap-3">
            <GoogleAuthButton />
            <ThemeToggle />
          </div>
        </div>

        <div className="flex-1 overflow-hidden relative">
          {children}
        </div>
      </main >
    </div >
  );
}

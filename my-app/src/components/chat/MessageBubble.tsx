import React from 'react';
import { Message } from '../../lib/types/chat';
import { cn } from '../../lib/util';

// Import the CSS for math (place this in your layout.tsx or here)
import 'katex/dist/katex.min.css';

interface MessageBubbleProps {
  message: Message;
  onCitationClick?: (page: number) => void;
}

export function MessageBubble({
  message,
  onCitationClick,
}: MessageBubbleProps) {
  const isUser = message.role === 'user';

  // Render message text with clickable inline citations like [3]
  const renderContentWithCitations = (text: string) => {
    const parts = text.split(/(\[\d+\])/g);

    return parts.map((part, index) => {
      const match = part.match(/\[(\d+)\]/);

      if (match) {
        const page = Number(match[1]);

        return (
          <button
            key={index}
            type="button"
            onClick={() => onCitationClick?.(page)}
            className="inline-flex items-center px-1 mx-0.5 text-sm font-medium text-teal-600 dark:text-teal-400 hover:underline focus:outline-none"
            title={`Go to page ${page}`}
          >
            [{page}]
          </button>
        );
      }

      return <span key={index}>{part}</span>;
    });
  };


  return (
    <div
      className={cn(
        'w-full py-6',
        isUser ? 'bg-white dark:bg-black' : 'bg-gray-50 dark:bg-gray-900'
      )}
    >
      <div className="max-w-3xl mx-auto px-4 flex gap-4">
        {/* Avatar */}
        <div
          className={cn(
            'w-8 h-8 rounded-full flex items-center justify-center font-bold text-sm',
            isUser
              ? 'bg-gray-200 dark:bg-gray-700 text-gray-700 dark:text-gray-200'
              : 'bg-teal-600 text-white'
          )}
        >
          {isUser ? 'U' : 'AI'}
        </div>

        <div className="flex-1 overflow-hidden">
          {/* TOOL / STATUS HEADER */}
          {!isUser && message.toolType && (
            <div className="mb-2 flex items-center gap-3 animate-fade-in">
              <div className="flex gap-1">
                <span className="w-2 h-2 rounded-full bg-teal-500 animate-bounce [animation-delay:-0.3s]" />
                <span className="w-2 h-2 rounded-full bg-teal-500 animate-bounce [animation-delay:-0.15s]" />
                <span className="w-2 h-2 rounded-full bg-teal-500 animate-bounce" />
              </div>

              <span className="text-sm font-medium text-teal-600 dark:text-teal-400 tracking-wide">
                {message.toolType.replace(/-/g, ' ')}
              </span>
            </div>
          )}

          {/* Role label */}
          <div className="font-semibold text-sm text-gray-900 dark:text-gray-100 mb-1">
            {isUser ? 'User' : 'Assistant'}
          </div>

          {/* Message content with inline citations */}
          <div className="prose dark:prose-invert max-w-none text-gray-800 dark:text-gray-200 leading-relaxed whitespace-pre-wrap">
            {renderContentWithCitations(message.content)}
          </div>
        </div>
      </div>

      {/* Local animation helpers */}
      <style jsx>{`
        @keyframes fade-in {
          from {
            opacity: 0;
            transform: translateY(-4px);
          }
          to {
            opacity: 1;
            transform: translateY(0);
          }
        }
        .animate-fade-in {
          animation: fade-in 0.25s ease-out;
        }
      `}</style>
    </div>
  );
}

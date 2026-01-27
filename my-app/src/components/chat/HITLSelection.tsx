'use client';

import React, { useState } from 'react';

interface SelectionOption {
    id: string;
    name: string;
    description?: string;
}

interface HITLSelectionProps {
    title?: string;
    message: string;
    options: SelectionOption[];
    onSelect: (item: SelectionOption | null) => void;
    allowNone?: boolean;
    noneLabel?: string;
    isLoading?: boolean;
}

export function HITLSelection({
    title,
    message,
    options,
    onSelect,
    allowNone = true,
    noneLabel = 'None of these',
    isLoading = false,
}: HITLSelectionProps) {
    const [selectedId, setSelectedId] = useState<string | null>(null);

    const handleSubmit = (e: React.FormEvent) => {
        e.preventDefault();
        if (selectedId === 'none') {
            onSelect(null);
        } else {
            const selected = options.find((opt) => opt.id === selectedId);
            if (selected) {
                onSelect(selected);
            }
        }
    };

    return (
        <div className="bg-gray-50 dark:bg-gray-900 rounded-xl p-4 border border-gray-200 dark:border-gray-700 my-3">
            {title && (
                <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-2">
                    {title}
                </h3>
            )}

            <p className="text-sm text-gray-600 dark:text-gray-400 mb-4">
                {message}
            </p>

            <form onSubmit={handleSubmit} className="space-y-3">
                <div className="space-y-2 max-h-60 overflow-y-auto pr-2 custom-scrollbar">
                    {options.map((option) => (
                        <label
                            key={option.id}
                            className={`
                                flex items-start gap-3 p-3 rounded-lg border cursor-pointer transition-all
                                ${selectedId === option.id
                                    ? 'border-teal-500 bg-teal-50 dark:bg-teal-900/20 ring-1 ring-teal-500'
                                    : 'border-gray-200 dark:border-gray-700 hover:border-teal-300 dark:hover:border-teal-800 bg-white dark:bg-gray-800'}
                            `}
                        >
                            <input
                                type="radio"
                                name="selection"
                                value={option.id}
                                checked={selectedId === option.id}
                                onChange={() => setSelectedId(option.id)}
                                className="mt-1 w-4 h-4 text-teal-600 focus:ring-teal-500 border-gray-300 dark:border-gray-600"
                                disabled={isLoading}
                            />
                            <div className="flex-1">
                                <span className="block font-medium text-gray-900 dark:text-gray-100 leading-tight">
                                    {option.name}
                                </span>
                                {option.description && (
                                    <span className="block text-xs text-gray-500 dark:text-gray-400 mt-1">
                                        {option.description}
                                    </span>
                                )}
                            </div>
                        </label>
                    ))}

                    {allowNone && (
                        <label
                            className={`
                                flex items-center gap-3 p-3 rounded-lg border cursor-pointer transition-all
                                ${selectedId === 'none'
                                    ? 'border-gray-400 bg-gray-100 dark:bg-gray-800 ring-1 ring-gray-400'
                                    : 'border-gray-200 dark:border-gray-700 hover:border-gray-300 dark:hover:border-gray-600 bg-white dark:bg-gray-800'}
                            `}
                        >
                            <input
                                type="radio"
                                name="selection"
                                value="none"
                                checked={selectedId === 'none'}
                                onChange={() => setSelectedId('none')}
                                className="w-4 h-4 text-gray-600 focus:ring-gray-500 border-gray-300 dark:border-gray-600"
                                disabled={isLoading}
                            />
                            <span className="font-medium text-gray-700 dark:text-gray-300">
                                {noneLabel}
                            </span>
                        </label>
                    )}
                </div>

                <div className="pt-2">
                    <button
                        type="submit"
                        disabled={!selectedId || isLoading}
                        className="w-full px-4 py-2 bg-teal-600 hover:bg-teal-700 text-white font-medium rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                        {isLoading ? 'Processing...' : 'Confirm Selection'}
                    </button>
                </div>
            </form>

            <style jsx>{`
                .custom-scrollbar::-webkit-scrollbar {
                    width: 4px;
                }
                .custom-scrollbar::-webkit-scrollbar-track {
                    background: transparent;
                }
                .custom-scrollbar::-webkit-scrollbar-thumb {
                    background: #cbd5e1;
                    border-radius: 10px;
                }
                .dark .custom-scrollbar::-webkit-scrollbar-thumb {
                    background: #475569;
                }
            `}</style>
        </div>
    );
}

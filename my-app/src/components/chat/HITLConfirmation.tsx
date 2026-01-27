'use client';

import React from 'react';

interface HITLConfirmationProps {
    title?: string;
    message: string;
    details?: Record<string, string | number | boolean>;
    onApprove: () => void;
    onReject: () => void;
    approveLabel?: string;
    rejectLabel?: string;
    isLoading?: boolean;
    variant?: 'default' | 'warning' | 'danger';
}

export function HITLConfirmation({
    title,
    message,
    details,
    onApprove,
    onReject,
    approveLabel = 'Yes, Proceed',
    rejectLabel = 'No, Cancel',
    isLoading = false,
    variant = 'default',
}: HITLConfirmationProps) {
    const variantStyles = {
        default: {
            border: 'border-teal-200 dark:border-teal-800',
            bg: 'bg-teal-50 dark:bg-teal-900/30',
            icon: '✓',
            iconBg: 'bg-teal-100 dark:bg-teal-800',
            iconColor: 'text-teal-600 dark:text-teal-400',
            approveBtn: 'bg-teal-600 hover:bg-teal-700',
        },
        warning: {
            border: 'border-amber-200 dark:border-amber-800',
            bg: 'bg-amber-50 dark:bg-amber-900/30',
            icon: '⚠',
            iconBg: 'bg-amber-100 dark:bg-amber-800',
            iconColor: 'text-amber-600 dark:text-amber-400',
            approveBtn: 'bg-amber-600 hover:bg-amber-700',
        },
        danger: {
            border: 'border-red-200 dark:border-red-800',
            bg: 'bg-red-50 dark:bg-red-900/30',
            icon: '!',
            iconBg: 'bg-red-100 dark:bg-red-800',
            iconColor: 'text-red-600 dark:text-red-400',
            approveBtn: 'bg-red-600 hover:bg-red-700',
        },
    };

    const styles = variantStyles[variant];

    return (
        <div className={`rounded-xl p-4 border ${styles.border} ${styles.bg} my-3`}>
            <div className="flex items-start gap-3">
                {/* Icon */}
                <div className={`flex-shrink-0 w-10 h-10 rounded-full ${styles.iconBg} flex items-center justify-center`}>
                    <span className={`text-lg font-bold ${styles.iconColor}`}>{styles.icon}</span>
                </div>

                <div className="flex-1">
                    {title && (
                        <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-1">
                            {title}
                        </h3>
                    )}

                    <p className="text-gray-700 dark:text-gray-300 mb-3">
                        {message}
                    </p>

                    {/* Details table */}
                    {details && Object.keys(details).length > 0 && (
                        <div className="bg-white dark:bg-gray-800 rounded-lg p-3 mb-4 border border-gray-200 dark:border-gray-700">
                            <table className="w-full text-sm">
                                <tbody>
                                    {Object.entries(details).map(([key, value]) => (
                                        <tr key={key} className="border-b border-gray-100 dark:border-gray-700 last:border-0">
                                            <td className="py-1.5 pr-3 font-medium text-gray-600 dark:text-gray-400 capitalize">
                                                {key.replace(/_/g, ' ')}
                                            </td>
                                            <td className="py-1.5 text-gray-900 dark:text-gray-100">
                                                {typeof value === 'boolean' ? (value ? 'Yes' : 'No') : String(value)}
                                            </td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        </div>
                    )}

                    {/* Action buttons */}
                    <div className="flex gap-3">
                        <button
                            onClick={onApprove}
                            disabled={isLoading}
                            className={`flex-1 px-4 py-2 ${styles.approveBtn} text-white font-medium rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed`}
                        >
                            {isLoading ? 'Processing...' : approveLabel}
                        </button>

                        <button
                            onClick={onReject}
                            disabled={isLoading}
                            className="flex-1 px-4 py-2 bg-gray-200 dark:bg-gray-700 hover:bg-gray-300 dark:hover:bg-gray-600 text-gray-700 dark:text-gray-200 font-medium rounded-lg transition-colors disabled:opacity-50"
                        >
                            {rejectLabel}
                        </button>
                    </div>
                </div>
            </div>
        </div>
    );
}

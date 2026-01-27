'use client';

import React, { useState } from 'react';

interface FormField {
    name: string;
    label: string;
    type: 'text' | 'email' | 'number' | 'date' | 'datetime' | 'select' | 'textarea';
    required?: boolean;
    placeholder?: string;
    options?: { value: string; label: string }[];  // For select type
    validation?: {
        min?: number;
        max?: number;
        pattern?: string;
        message?: string;
    };
}

interface ToolInfo {
    id: string;
    usage: string;
    required_params: string[];
    optional_params: string[];
}

interface HITLFormInputProps {
    title?: string;
    description?: string;
    tool_info?: ToolInfo;
    fields: FormField[];
    onSubmit: (data: Record<string, string | number>) => void;
    onCancel?: () => void;
    submitLabel?: string;
    cancelLabel?: string;
    isLoading?: boolean;
}

export function HITLFormInput({
    title,
    description,
    tool_info,
    fields,
    onSubmit,
    onCancel,
    submitLabel = 'Submit',
    cancelLabel = 'Cancel',
    isLoading = false,
}: HITLFormInputProps) {
    const [formData, setFormData] = useState<Record<string, string | number>>({});
    const [errors, setErrors] = useState<Record<string, string>>({});

    const handleChange = (name: string, value: string | number) => {
        setFormData((prev) => ({ ...prev, [name]: value }));
        // Clear error when field is edited
        if (errors[name]) {
            setErrors((prev) => {
                const newErrors = { ...prev };
                delete newErrors[name];
                return newErrors;
            });
        }
    };

    const validate = (): boolean => {
        const newErrors: Record<string, string> = {};

        for (const field of fields) {
            const value = formData[field.name];

            // Required check
            if (field.required && (value === undefined || value === '')) {
                newErrors[field.name] = `${field.label} is required`;
                continue;
            }

            // Pattern validation
            if (field.validation?.pattern && typeof value === 'string') {
                const regex = new RegExp(field.validation.pattern);
                if (!regex.test(value)) {
                    newErrors[field.name] = field.validation.message || `Invalid ${field.label}`;
                }
            }

            // Number range validation
            if (field.type === 'number' && typeof value === 'number') {
                if (field.validation?.min !== undefined && value < field.validation.min) {
                    newErrors[field.name] = `${field.label} must be at least ${field.validation.min}`;
                }
                if (field.validation?.max !== undefined && value > field.validation.max) {
                    newErrors[field.name] = `${field.label} must be at most ${field.validation.max}`;
                }
            }
        }

        setErrors(newErrors);
        return Object.keys(newErrors).length === 0;
    };

    const handleSubmit = (e: React.FormEvent) => {
        e.preventDefault();
        if (validate()) {
            onSubmit(formData);
        }
    };

    const renderField = (field: FormField) => {
        const baseClasses = `
      w-full px-3 py-2 rounded-lg border transition-colors
      bg-white dark:bg-gray-800
      border-gray-300 dark:border-gray-600
      focus:border-teal-500 dark:focus:border-teal-400
      focus:outline-none focus:ring-2 focus:ring-teal-500/20
      text-gray-900 dark:text-gray-100
      placeholder-gray-400 dark:placeholder-gray-500
      ${errors[field.name] ? 'border-red-500 dark:border-red-400' : ''}
    `;

        switch (field.type) {
            case 'textarea':
                return (
                    <textarea
                        name={field.name}
                        placeholder={field.placeholder}
                        value={formData[field.name] || ''}
                        onChange={(e) => handleChange(field.name, e.target.value)}
                        className={`${baseClasses} min-h-[100px] resize-y`}
                        disabled={isLoading}
                    />
                );

            case 'select':
                return (
                    <select
                        name={field.name}
                        value={formData[field.name] || ''}
                        onChange={(e) => handleChange(field.name, e.target.value)}
                        className={baseClasses}
                        disabled={isLoading}
                    >
                        <option value="">{field.placeholder || 'Select...'}</option>
                        {field.options?.map((opt) => (
                            <option key={opt.value} value={opt.value}>
                                {opt.label}
                            </option>
                        ))}
                    </select>
                );

            case 'number':
                return (
                    <input
                        type="number"
                        name={field.name}
                        placeholder={field.placeholder}
                        value={formData[field.name] || ''}
                        onChange={(e) => handleChange(field.name, parseFloat(e.target.value) || 0)}
                        min={field.validation?.min}
                        max={field.validation?.max}
                        className={baseClasses}
                        disabled={isLoading}
                    />
                );

            case 'datetime':
                return (
                    <input
                        type="datetime-local"
                        name={field.name}
                        placeholder={field.placeholder}
                        value={formData[field.name] || ''}
                        onChange={(e) => handleChange(field.name, e.target.value)}
                        className={baseClasses}
                        disabled={isLoading}
                    />
                );

            case 'email':
                return (
                    <input
                        type="email"
                        name={field.name}
                        placeholder={field.placeholder || 'email@example.com'}
                        value={formData[field.name] || ''}
                        onChange={(e) => handleChange(field.name, e.target.value)}
                        className={baseClasses}
                        disabled={isLoading}
                    />
                );

            default:
                return (
                    <input
                        type={field.type}
                        name={field.name}
                        placeholder={field.placeholder}
                        value={formData[field.name] || ''}
                        onChange={(e) => handleChange(field.name, e.target.value)}
                        className={baseClasses}
                        disabled={isLoading}
                    />
                );
        }
    };

    return (
        <div className="bg-gray-50 dark:bg-gray-900 rounded-xl p-4 border border-gray-200 dark:border-gray-700 my-3">
            {/* Tool Info Banner */}
            {tool_info && (
                <div className="mb-4 p-3 bg-blue-50 dark:bg-blue-900/30 rounded-lg border border-blue-200 dark:border-blue-800">
                    <div className="flex items-center gap-2 mb-2">
                        <span className="flex h-6 w-6 items-center justify-center rounded-full bg-blue-100 dark:bg-blue-800">
                            <svg className="h-3.5 w-3.5 text-blue-600 dark:text-blue-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                            </svg>
                        </span>
                        <span className="text-sm font-semibold text-blue-700 dark:text-blue-300 uppercase tracking-wide">
                            {tool_info.id.replace(/_/g, ' ')}
                        </span>
                    </div>
                    {tool_info.usage && (
                        <p className="text-sm text-blue-600 dark:text-blue-400 mb-2">
                            {tool_info.usage}
                        </p>
                    )}
                    <div className="flex flex-wrap gap-2 text-xs">
                        {tool_info.required_params.length > 0 && (
                            <span className="inline-flex items-center gap-1 px-2 py-1 rounded-full bg-red-100 dark:bg-red-900/50 text-red-700 dark:text-red-300">
                                <span className="font-medium">Required:</span>
                                {tool_info.required_params.map(p => p.replace(/_/g, ' ')).join(', ')}
                            </span>
                        )}
                        {tool_info.optional_params.length > 0 && (
                            <span className="inline-flex items-center gap-1 px-2 py-1 rounded-full bg-gray-100 dark:bg-gray-800 text-gray-600 dark:text-gray-400">
                                <span className="font-medium">Optional:</span>
                                {tool_info.optional_params.map(p => p.replace(/_/g, ' ')).join(', ')}
                            </span>
                        )}
                    </div>
                </div>
            )}

            {title && (
                <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-2">
                    {title}
                </h3>
            )}

            {description && (
                <p className="text-sm text-gray-600 dark:text-gray-400 mb-4">
                    {description}
                </p>
            )}

            <form onSubmit={handleSubmit} className="space-y-4">
                {fields.map((field) => (
                    <div key={field.name}>
                        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                            {field.label}
                            {field.required && <span className="text-red-500 ml-1">*</span>}
                        </label>
                        {renderField(field)}
                        {errors[field.name] && (
                            <p className="mt-1 text-sm text-red-500">{errors[field.name]}</p>
                        )}
                    </div>
                ))}

                <div className="flex gap-3 pt-2">
                    <button
                        type="submit"
                        disabled={isLoading}
                        className="flex-1 px-4 py-2 bg-teal-600 hover:bg-teal-700 text-white font-medium rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                        {isLoading ? 'Submitting...' : submitLabel}
                    </button>

                    {onCancel && (
                        <button
                            type="button"
                            onClick={onCancel}
                            disabled={isLoading}
                            className="px-4 py-2 bg-gray-200 dark:bg-gray-700 hover:bg-gray-300 dark:hover:bg-gray-600 text-gray-700 dark:text-gray-200 font-medium rounded-lg transition-colors disabled:opacity-50"
                        >
                            {cancelLabel}
                        </button>
                    )}
                </div>
            </form>
        </div>
    );
}

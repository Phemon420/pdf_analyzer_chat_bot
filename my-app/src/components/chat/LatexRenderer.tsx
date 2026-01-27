'use client';

import React from 'react';
import katex from 'katex';
import 'katex/dist/katex.min.css';

interface LatexRendererProps {
    content: string;
    className?: string;
}

/**
 * Renders text with inline and block LaTeX math expressions.
 * 
 * Supports:
 * - Inline math: $...$ or \(...\)
 * - Block/display math: $$...$$ or \[...\]
 */
export function LatexRenderer({ content, className = '' }: LatexRendererProps) {
    const renderLatex = (text: string): React.ReactNode[] => {
        const parts: React.ReactNode[] = [];
        let lastIndex = 0;
        let key = 0;

        // Combined regex for both inline and block math
        // Block: $$...$$ or \[...\]
        // Inline: $...$ (non-greedy) or \(...\)
        const mathRegex = /(\$\$[\s\S]*?\$\$|\\\[[\s\S]*?\\\]|\$[^$\n]+?\$|\\\(.*?\\\))/g;

        let match;
        while ((match = mathRegex.exec(text)) !== null) {
            // Add text before the math
            if (match.index > lastIndex) {
                parts.push(
                    <span key={key++}>{text.slice(lastIndex, match.index)}</span>
                );
            }

            const mathContent = match[0];
            let latex = '';
            let isBlock = false;

            // Determine type and extract LaTeX
            if (mathContent.startsWith('$$')) {
                latex = mathContent.slice(2, -2);
                isBlock = true;
            } else if (mathContent.startsWith('\\[')) {
                latex = mathContent.slice(2, -2);
                isBlock = true;
            } else if (mathContent.startsWith('$')) {
                latex = mathContent.slice(1, -1);
                isBlock = false;
            } else if (mathContent.startsWith('\\(')) {
                latex = mathContent.slice(2, -2);
                isBlock = false;
            }

            try {
                const html = katex.renderToString(latex.trim(), {
                    throwOnError: false,
                    displayMode: isBlock,
                    strict: false,
                });

                if (isBlock) {
                    parts.push(
                        <div
                            key={key++}
                            className="my-4 overflow-x-auto"
                            dangerouslySetInnerHTML={{ __html: html }}
                        />
                    );
                } else {
                    parts.push(
                        <span
                            key={key++}
                            dangerouslySetInnerHTML={{ __html: html }}
                        />
                    );
                }
            } catch (error) {
                // If LaTeX parsing fails, show original text
                parts.push(<span key={key++} className="text-red-500">{mathContent}</span>);
            }

            lastIndex = match.index + match[0].length;
        }

        // Add remaining text
        if (lastIndex < text.length) {
            parts.push(<span key={key++}>{text.slice(lastIndex)}</span>);
        }

        return parts;
    };

    return (
        <span className={className}>
            {renderLatex(content)}
        </span>
    );
}

/**
 * Checks if a string contains LaTeX math expressions
 */
export function containsLatex(text: string): boolean {
    return /(\$\$[\s\S]*?\$\$|\\\[[\s\S]*?\\\]|\$[^$\n]+?\$|\\\(.*?\\\))/.test(text);
}

'use client';

import React from 'react';
import { LatexRenderer } from './LatexRenderer';
import { cn } from '../../lib/util';

interface PQA {
    question: string;
    answer: string;
}

interface Paragraph {
    content: string;
    math_formula?: string;
}

interface AccordionItem {
    heading: string;
    content: string;
    'hyper-link'?: string;
}

interface PopupItem {
    title: string;
    description: string;
}

interface EndToggleButton {
    heading: string;
    content: string;
}

interface EndToggle {
    heading: string;
    content: string;
    buttons: EndToggleButton[];
}

interface StructuredData {
    pqa?: PQA[];
    paragraphs?: Paragraph[];
    accordion?: AccordionItem[];
    pop_up?: PopupItem[];
    end_toggle?: EndToggle;
}

interface StructuredRendererProps {
    data: StructuredData;
}

export function StructuredRenderer({ data }: StructuredRendererProps) {
    return (
        <div className="flex flex-col gap-6 animate-in fade-in slide-in-from-bottom-2 duration-500">

            {/* PQA - Questions & Answers */}
            {data.pqa && data.pqa.length > 0 && (
                <div className="flex flex-col gap-4">
                    {data.pqa.map((item, i) => (
                        <div key={i} className="bg-teal-50/50 dark:bg-teal-900/10 border-l-4 border-teal-500 p-4 rounded-r-xl">
                            <h4 className="font-bold text-teal-800 dark:text-teal-300 mb-2 flex items-center gap-2">
                                <span className="bg-teal-500 text-white w-5 h-5 rounded-full flex items-center justify-center text-[10px]">Q</span>
                                {item.question}
                            </h4>
                            <p className="text-gray-700 dark:text-gray-300 leading-relaxed italic">
                                {item.answer}
                            </p>
                        </div>
                    ))}
                </div>
            )}

            {/* Paragraphs with Math support */}
            {data.paragraphs && data.paragraphs.length > 0 && (
                <div className="flex flex-col gap-4">
                    {data.paragraphs.map((p, i) => (
                        <div key={i} className="text-gray-800 dark:text-gray-200 leading-relaxed">
                            <LatexRenderer content={p.content} />
                            {p.math_formula && (
                                <div className="my-4 p-4 bg-gray-100 dark:bg-gray-800 rounded-lg overflow-x-auto shadow-inner">
                                    <LatexRenderer content={`$$${p.math_formula}$$`} />
                                </div>
                            )}
                        </div>
                    ))}
                </div>
            )}

            {/* Accordions */}
            {data.accordion && data.accordion.length > 0 && (
                <div className="flex flex-col gap-3">
                    {data.accordion.map((item, i) => (
                        <details key={i} className="group border border-gray-200 dark:border-gray-700 rounded-xl bg-white dark:bg-gray-800/50 transition-all hover:shadow-md overflow-hidden">
                            <summary className="flex items-center justify-between p-4 cursor-pointer font-semibold list-none text-gray-900 dark:text-gray-100">
                                <div className="flex items-center gap-3">
                                    <div className="w-2 h-2 rounded-full bg-teal-500" />
                                    {item.heading}
                                </div>
                                <span className="transition-transform group-open:rotate-180 text-gray-400">
                                    <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="m6 9 6 6 6-6" /></svg>
                                </span>
                            </summary>
                            <div className="p-4 pt-0 text-gray-600 dark:text-gray-400 border-t border-gray-100 dark:border-gray-800">
                                <p className="mb-2 leading-relaxed">{item.content}</p>
                                {item['hyper-link'] && (
                                    <a href="#" className="text-teal-600 dark:text-teal-400 text-sm font-medium hover:underline inline-flex items-center gap-1">
                                        {item['hyper-link']}
                                        <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6" /><polyline points="15 3 21 3 21 9" /><line x1="10" y1="14" x2="21" y2="3" /></svg>
                                    </a>
                                )}
                            </div>
                        </details>
                    ))}
                </div>
            )}

            {/* Pop-ups / Highlight Cards */}
            {data.pop_up && data.pop_up.length > 0 && (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    {data.pop_up.map((popup, i) => (
                        <div key={i} className="p-5 rounded-2xl bg-gradient-to-br from-white to-gray-50 dark:from-gray-800 dark:to-gray-900 border border-gray-200 dark:border-gray-700 shadow-sm transition-transform hover:-translate-y-1">
                            <div className="flex items-center gap-3 mb-2">
                                <div className="p-2 bg-teal-100 dark:bg-teal-900/40 rounded-lg text-teal-600 dark:text-teal-400">
                                    <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M14.5 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7.5L14.5 2z" /><polyline points="14 2 14 8 20 8" /></svg>
                                </div>
                                <h5 className="font-bold text-gray-900 dark:text-gray-100">{popup.title}</h5>
                            </div>
                            <p className="text-sm text-gray-600 dark:text-gray-400 leading-relaxed">
                                {popup.description}
                            </p>
                        </div>
                    ))}
                </div>
            )}

            {/* End Toggle */}
            {data.end_toggle && (
                <div className="mt-4 p-8 rounded-3xl bg-gray-900 text-white shadow-2xl relative overflow-hidden group">
                    <div className="absolute top-0 right-0 w-64 h-64 bg-teal-500/10 rounded-full blur-3xl -mr-32 -mt-32" />
                    <div className="relative z-10">
                        <h3 className="text-2xl font-bold mb-3 bg-gradient-to-r from-teal-400 to-emerald-400 bg-clip-text text-transparent">
                            {data.end_toggle.heading}
                        </h3>
                        <p className="text-gray-400 mb-8 max-w-lg leading-relaxed font-light tracking-wide text-lg">
                            {data.end_toggle.content}
                        </p>
                        <div className="flex flex-wrap gap-4">
                            {data.end_toggle.buttons.map((btn, i) => (
                                <button
                                    key={i}
                                    className="px-6 py-3 rounded-2xl bg-white/10 hover:bg-white/20 border border-white/10 hover:border-white/25 transition-all flex flex-col items-start gap-1 group/btn"
                                >
                                    <span className="font-bold text-teal-400 group-hover/btn:text-teal-300 transition-colors uppercase text-xs tracking-widest">{btn.heading}</span>
                                    <span className="text-sm text-gray-300 font-medium">{btn.content}</span>
                                </button>
                            ))}
                        </div>
                    </div>
                </div>
            )}

        </div>
    );
}

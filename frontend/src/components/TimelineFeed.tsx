"use client";

import { motion } from "framer-motion";
import { Bot, Activity, Play, CheckCircle2, Clock, Edit2, Save, X, FileText, FileSpreadsheet, File } from "lucide-react";
import { cn } from "@/lib/utils";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import rehypeRaw from "rehype-raw";
import React, { useState, useEffect } from "react";
// Dynamic import for Tauri to avoid SSR issues
import dynamic from 'next/dynamic';

export type Step = {
    type: "Reasoning" | "Decision" | "Action";
    content: string;
    timestamp: string;
    attachment?: {
        type: "image" | "video" | "audio" | "options" | "web_result";
        url?: string;
        name?: string;
        data?: any;
        screenshot?: string;
    };
};

interface TimelineFeedProps {
    steps: Step[];
    onOptionSelect?: (value: string) => void;
}

export function TimelineFeed({ steps, onOptionSelect }: TimelineFeedProps) {
    if (steps.length === 0) return null;

    return (
        <div className="w-full mx-auto mt-12 px-4 relative pb-20">
            <div className="absolute left-8 top-0 bottom-0 w-px bg-gradient-to-b from-transparent via-primary/20 to-transparent" />

            <div className="space-y-8">
                {steps.map((step, i) => (
                    <motion.div
                        key={i}
                        initial={{ opacity: 0, x: -20 }}
                        animate={{ opacity: 1, x: 0 }}
                        transition={{ delay: i * 0.1 }}
                        className="relative pl-16 group"
                    >
                        {/* Timeline Node */}
                        <div className={cn(
                            "absolute left-[26px] -translate-x-1/2 top-0 w-3 h-3 rounded-full border-2 z-10 bg-background transition-colors duration-300",
                            step.type === "Reasoning" && "border-blue-500 group-hover:bg-blue-500",
                            step.type === "Decision" && "border-yellow-500 group-hover:bg-yellow-500",
                            step.type === "Action" && "border-green-500 group-hover:bg-green-500"
                        )} />

                        <div className={cn(
                            "p-5 rounded-2xl border transition-all duration-300 hover:scale-[1.01] relative overflow-hidden",
                            "bg-[#0F0F16] backdrop-blur-md", // Darker solid/semi-transparent background for readability
                            step.type === "Reasoning" && "border-blue-500/20 hover:border-blue-500/40 shadow-lg shadow-blue-900/10",
                            step.type === "Decision" && "border-yellow-500/20 hover:border-yellow-500/40 shadow-lg shadow-yellow-900/10",
                            step.type === "Action" && "border-emerald-500/20 hover:border-emerald-500/40 shadow-lg shadow-emerald-900/10"
                        )}>
                            {/* Subtle top highlight */}
                            <div className={cn(
                                "absolute top-0 left-0 right-0 h-[1px] bg-gradient-to-r from-transparent via-white/10 to-transparent",
                                step.type === "Reasoning" && "via-blue-500/20",
                                step.type === "Decision" && "via-yellow-500/20",
                                step.type === "Action" && "via-emerald-500/20"
                            )} />

                            <div className="flex justify-between items-start mb-3">
                                <div className="flex items-center gap-2">
                                    <div className={cn(
                                        "p-1.5 rounded-lg border",
                                        step.type === "Reasoning" && "bg-blue-500/10 border-blue-500/20 text-blue-400",
                                        step.type === "Decision" && "bg-yellow-500/10 border-yellow-500/20 text-yellow-400",
                                        step.type === "Action" && "bg-emerald-500/10 border-emerald-500/20 text-emerald-400"
                                    )}>
                                        {step.type === "Reasoning" && <Bot className="w-4 h-4" />}
                                        {step.type === "Decision" && <Activity className="w-4 h-4" />}
                                        {step.type === "Action" && <Play className="w-4 h-4" />}
                                    </div>
                                    <span className={cn(
                                        "text-xs font-bold uppercase tracking-wider",
                                        step.type === "Reasoning" && "text-blue-400",
                                        step.type === "Decision" && "text-yellow-400",
                                        step.type === "Action" && "text-emerald-400"
                                    )}>
                                        {step.type}
                                    </span>
                                </div>
                                <span className="text-xs text-slate-500 font-mono flex items-center gap-1.5 bg-black/20 px-2 py-1 rounded-md border border-white/5">
                                    <Clock className="w-3 h-3" />
                                    {step.timestamp}
                                </span>
                            </div>

                            <div className="text-slate-300 leading-relaxed text-sm font-light prose prose-invert max-w-none">
                                <ReactMarkdown
                                    remarkPlugins={[remarkGfm]}
                                    rehypePlugins={[rehypeRaw]}
                                    components={{
                                        table: ({ node, ...props }) => <div className="overflow-x-auto my-2"><table {...props} className="w-full border-collapse border border-white/10 text-xs" /></div>,
                                        th: ({ node, ...props }) => <th {...props} className="border border-white/10 p-2 bg-white/5 text-left font-semibold text-white/70" />,
                                        td: ({ node, ...props }) => <td {...props} className="border border-white/10 p-2 text-white/60 whitespace-nowrap" />,
                                        p: ({ node, ...props }) => <p {...props} className="mb-2 last:mb-0" />,
                                        string: ({ node, ...props }: any) => <span {...props} />,
                                        module: ({ node, ...props }: any) => <span {...props} />,
                                    } as any}
                                >
                                    {step.content}
                                </ReactMarkdown>

                                {/* Options Buttons */}
                                {step.attachment && step.attachment.type === "options" && (
                                    <div className="mt-4 grid grid-cols-1 md:grid-cols-2 gap-2">
                                        {(step.attachment as any).data.map((opt: any, idx: number) => (
                                            <button
                                                key={idx}
                                                onClick={() => onOptionSelect && onOptionSelect(opt.value)}
                                                className="px-3 py-2 text-left bg-white/5 hover:bg-white/10 border border-white/10 rounded-lg text-xs text-slate-300 transition-colors flex items-center gap-2 group/btn"
                                            >
                                                <div className="w-1.5 h-1.5 rounded-full bg-emerald-500/50 group-hover/btn:bg-emerald-400" />
                                                <span className="truncate">{opt.label}</span>
                                            </button>
                                        ))}
                                    </div>
                                )}

                                {/* Web Result Attachment */}
                                {step.attachment && step.attachment.type === "web_result" && (
                                    <WebResultViewer
                                        initialData={(step.attachment as any).data}
                                        url={(step.attachment as any).url}
                                        screenshot={(step.attachment as any).screenshot}
                                    />
                                )}
                            </div>
                        </div>
                    </motion.div>
                ))}
            </div>
        </div>
    );
}

// Separate component for Web Results to handle saving logic
function WebResultViewer({ initialData, url, screenshot }: { initialData: any, url?: string, screenshot?: string }) {
    const [data, setData] = useState(initialData);
    const [isEditing, setIsEditing] = useState(false);
    const [editedContent, setEditedContent] = useState("");
    const [saveStatus, setSaveStatus] = useState<string | null>(null);

    useEffect(() => {
        setData(initialData);
    }, [initialData]);

    const handleEdit = () => {
        if (!isEditing) {
            // Enter edit mode: Convert data to string for textarea
            const text = typeof data === 'string' ? data : JSON.stringify(data, null, 2);
            setEditedContent(text);
        } else {
            // Save edits (locally to state)
            try {
                // Try to parse back to JSON if it looks like JSON
                if (editedContent.trim().startsWith("{") || editedContent.trim().startsWith("[")) {
                    const parsed = JSON.parse(editedContent);
                    setData(parsed);
                } else {
                    setData(editedContent);
                }
            } catch (e) {
                // If parse fails, just save as string
                setData(editedContent);
            }
        }
        setIsEditing(!isEditing);
    };

    const handleSaveAs = async (format: string) => {
        setSaveStatus("Saving...");

        try {
            // Dynamic imports for Tauri
            const { save } = await import('@tauri-apps/plugin-dialog');
            const { orchestrateWebTask } = await import('@/lib/api');

            // 1. Open Save Dialog
            const filePath = await save({
                filters: [{
                    name: format.toUpperCase(),
                    extensions: [format]
                }]
            });

            if (!filePath) {
                setSaveStatus(null);
                return; // User cancelled
            }

            // 2. Send to Backend with Path
            const payload = {
                data: data,
                format: format,
                filepath: filePath // Backend will use this
            };

            const result = await orchestrateWebTask("ignored", "save_result_as_file", JSON.stringify(payload));

            if (result.file) {
                setSaveStatus(`Saved to ${result.file}`);
                setTimeout(() => setSaveStatus(null), 3000);
            } else {
                setSaveStatus(`Error: ${result.status}`);
            }

        } catch (e) {
            console.error(e);
            setSaveStatus(`Error: ${e}`);
        }
    };

    const isTable = Array.isArray(data) && data.length > 0 && typeof data[0] === 'object';

    return (
        <div className="mt-4 bg-black/40 rounded-xl border border-white/10 overflow-hidden shadow-2xl backdrop-blur-sm">
            {/* Header / Toolbar */}
            <div className="flex items-center justify-between px-4 py-3 bg-white/5 border-b border-white/5">
                <div className="flex items-center gap-2">
                    <span className="text-xs font-semibold text-emerald-400 uppercase tracking-widest">Web Result</span>
                    {saveStatus && <span className="text-xs text-slate-400 animate-pulse">| {saveStatus}</span>}
                </div>

                <div className="flex gap-2">
                    <button
                        onClick={handleEdit}
                        className={cn(
                            "flex items-center gap-1.5 px-3 py-1.5 rounded-md text-[10px] font-medium transition-all",
                            isEditing
                                ? "bg-emerald-500/20 text-emerald-400 border border-emerald-500/30"
                                : "bg-white/5 hover:bg-white/10 text-slate-300 border border-white/10"
                        )}
                    >
                        {isEditing ? <CheckCircle2 className="w-3 h-3" /> : <Edit2 className="w-3 h-3" />}
                        {isEditing ? "Done" : "Edit"}
                    </button>

                    <div className="w-px h-6 bg-white/10 mx-1" />

                    <button onClick={() => handleSaveAs('docx')} className="flex items-center gap-1.5 px-3 py-1.5 rounded-md text-[10px] font-medium bg-blue-500/10 hover:bg-blue-500/20 text-blue-300 border border-blue-500/20 transition-all">
                        <FileText className="w-3 h-3" /> Word
                    </button>
                    <button onClick={() => handleSaveAs('pdf')} className="flex items-center gap-1.5 px-3 py-1.5 rounded-md text-[10px] font-medium bg-red-500/10 hover:bg-red-500/20 text-red-300 border border-red-500/20 transition-all">
                        <File className="w-3 h-3" /> PDF
                    </button>
                    {isTable && (
                        <button onClick={() => handleSaveAs('xlsx')} className="flex items-center gap-1.5 px-3 py-1.5 rounded-md text-[10px] font-medium bg-emerald-500/10 hover:bg-emerald-500/20 text-emerald-300 border border-emerald-500/20 transition-all">
                            <FileSpreadsheet className="w-3 h-3" /> Excel
                        </button>
                    )}
                </div>
            </div>

            {/* Editing Mode */}
            {isEditing ? (
                <div className="p-0">
                    <textarea
                        value={editedContent}
                        onChange={(e) => setEditedContent(e.target.value)}
                        className="w-full h-[300px] bg-[#0F0F16] p-4 text-xs font-mono text-slate-300 focus:outline-none resize-y"
                    />
                </div>
            ) : (
                /* Data Preview */
                <div className="p-0">
                    {/* Screenshot Banner */}
                    {screenshot && (
                        <div className="relative group/shot border-b border-white/5 bg-black/50">
                            <div className="h-1 bg-gradient-to-r from-transparent via-emerald-500/50 to-transparent opacity-50" />
                            <div className="py-2 text-center">
                                <span className="text-[10px] text-slate-500">Screenshot captured successfully</span>
                            </div>
                        </div>
                    )}

                    <div className="p-4 overflow-x-auto">
                        {/* SPECIAL CASE: Title + Content List (Common Web Scrape Format) */}
                        {data && typeof data === 'object' && data.title && Array.isArray(data.content) ? (
                            <div className="space-y-3">
                                <h3 className="text-sm font-bold text-slate-100 border-b border-white/10 pb-2">
                                    {data.title}
                                </h3>
                                <ul className="space-y-1.5">
                                    {data.content.map((item: string, idx: number) => (
                                        <li key={idx} className="text-xs text-slate-300 flex items-start gap-2">
                                            <span className="text-emerald-500/50 mt-1">•</span>
                                            <span>{item}</span>
                                        </li>
                                    ))}
                                </ul>
                            </div>
                        ) : isTable ? (
                            <table className="w-full text-left text-xs text-slate-300">
                                <thead>
                                    <tr className="border-b border-white/10">
                                        {Object.keys(data[0]).slice(0, 6).map(key => (
                                            <th key={key} className="pb-3 pl-2 font-semibold text-slate-400 uppercase text-[10px] tracking-wider">{key}</th>
                                        ))}
                                        {Object.keys(data[0]).length > 6 && <th className="pb-3 text-slate-500">...</th>}
                                    </tr>
                                </thead>
                                <tbody>
                                    {data.map((row: any, i: number) => (
                                        <tr key={i} className="border-b border-white/5 last:border-0 hover:bg-white/5 transition-colors">
                                            {Object.values(row).slice(0, 6).map((val: any, j: number) => (
                                                <td key={j} className="py-2 pl-2 pr-4 truncate max-w-[200px] text-slate-400">{String(val)}</td>
                                            ))}
                                            {Object.keys(row).length > 6 && <td className="py-2 text-slate-600">...</td>}
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        ) : (
                            <pre className="text-xs text-slate-300 whitespace-pre-wrap font-mono leading-relaxed">
                                {typeof data === 'string' ? data : JSON.stringify(data, null, 2)}
                            </pre>
                        )}
                    </div>
                </div>
            )}

            {url && (
                <div className="px-4 py-2 bg-white/5 text-[10px] border-t border-white/5 flex items-center justify-between">
                    <span className="text-slate-500 font-mono truncate max-w-[300px]">{url}</span>
                    <span className="text-slate-600">Source</span>
                </div>
            )}
        </div>
    );
}

"use client";

import { motion, AnimatePresence } from "framer-motion";
import { Bot, Activity, Play, CheckCircle2, Clock, Edit2, Save, X, FileText, FileSpreadsheet, File } from "lucide-react";
import { cn } from "@/lib/utils";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import rehypeRaw from "rehype-raw";
import React, { useState, useEffect } from "react";
// Dynamic import for Tauri to avoid SSR issues
import dynamic from 'next/dynamic';
import { ResultCard } from "./ResultCard";

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
    const [collapsedSteps, setCollapsedSteps] = useState<number[]>([]);

    if (steps.length === 0) return null;

    const toggleCollapse = (index: number) => {
        setCollapsedSteps(prev =>
            prev.includes(index) ? prev.filter(i => i !== index) : [...prev, index]
        );
    };

    return (
        <div className="w-full max-w-5xl mx-auto mt-16 px-6 relative pb-32">
            {/* Main Timeline Thread */}
            <div className="absolute left-[34px] top-0 bottom-0 w-px bg-gradient-to-b from-primary/50 via-primary/10 to-transparent" />

            <div className="space-y-12">
                {steps.map((step, i) => {
                    const isLast = i === steps.length - 1;
                    const isCollapsed = collapsedSteps.includes(i) || (step.type === "Reasoning" && !isLast && steps.some(s => s.type === "Action"));

                    return (
                        <motion.div
                            key={i}
                            initial={{ opacity: 0, x: -30 }}
                            animate={{ opacity: 1, x: 0 }}
                            transition={{ delay: i * 0.1, duration: 0.8, type: "spring" }}
                            className="relative pl-20 group"
                        >
                            {/* Timeline Node refinement */}
                            <div className={cn(
                                "absolute left-[34px] -translate-x-1/2 top-4 w-4 h-4 rounded-full border-2 z-10 transition-all duration-500",
                                isLast && "ring-4 ring-primary/20",
                                step.type === "Reasoning" && "border-blue-500 bg-blue-500/20",
                                step.type === "Decision" && "border-amber-500 bg-amber-500/20",
                                step.type === "Action" && "border-emerald-500 bg-emerald-500/20 shadow-[0_0_15px_rgba(16,185,129,0.5)]"
                            )}>
                                {isLast && <div className="absolute inset-0 rounded-full bg-primary animate-ping opacity-40" />}
                            </div>

                            {/* Card Construction */}
                            <div className={cn(
                                "premium-card p-6 border-white/5 relative",
                                step.type === "Reasoning" && "opacity-80 hover:opacity-100",
                                isLast && "border-primary/20 shadow-[0_0_50px_-12px_oklch(0.68_0.28_280/0.15)]"
                            )}>
                                {/* Glass Edge Glow */}
                                <div className={cn(
                                    "absolute top-0 left-0 bottom-0 w-[2px] opacity-40",
                                    step.type === "Reasoning" && "bg-blue-500",
                                    step.type === "Decision" && "bg-amber-500",
                                    step.type === "Action" && "bg-emerald-500"
                                )} />

                                {/* Card Header */}
                                <div className="flex justify-between items-center mb-4">
                                    <div className="flex items-center gap-3">
                                        <div className={cn(
                                            "p-2 rounded-xl",
                                            step.type === "Reasoning" && "bg-blue-500/10 text-blue-400",
                                            step.type === "Decision" && "bg-amber-500/10 text-amber-400",
                                            step.type === "Action" && "bg-emerald-500/10 text-emerald-400"
                                        )}>
                                            {step.type === "Reasoning" && <Bot className="w-5 h-5" />}
                                            {step.type === "Decision" && <Activity className="w-5 h-5" />}
                                            {step.type === "Action" && <Play className="w-5 h-5" />}
                                        </div>
                                        <div>
                                            <span className={cn(
                                                "text-[10px] font-black uppercase tracking-[0.2em]",
                                                step.type === "Reasoning" && "text-blue-500/70",
                                                step.type === "Decision" && "text-amber-500/70",
                                                step.type === "Action" && "text-emerald-500/70"
                                            )}>
                                                {step.type}
                                            </span>
                                            <h4 className="text-sm font-bold text-foreground leading-none mt-1">
                                                {step.type === "Reasoning" ? "Analytical Thinking" : step.type === "Decision" ? "Strategy Selection" : "Process Execution"}
                                            </h4>
                                        </div>
                                    </div>

                                    <div className="flex items-center gap-4">
                                        <span className="text-[10px] text-muted-foreground font-mono tracking-tighter opacity-70">
                                            {step.timestamp}
                                        </span>
                                        {step.type === "Reasoning" && !isLast && (
                                            <button
                                                onClick={() => toggleCollapse(i)}
                                                className="text-[10px] font-bold text-primary hover:text-white uppercase tracking-widest transition-colors"
                                            >
                                                {isCollapsed ? "[ Show ]" : "[ Hide ]"}
                                            </button>
                                        )}
                                    </div>
                                </div>

                                {/* Card Content */}
                                <AnimatePresence initial={false}>
                                    {!isCollapsed && (
                                        <motion.div
                                            initial={{ height: 0, opacity: 0 }}
                                            animate={{ height: "auto", opacity: 1 }}
                                            exit={{ height: 0, opacity: 0 }}
                                            className="overflow-hidden"
                                        >
                                            <div className="text-foreground leading-relaxed text-base font-light pt-2 border-t border-border mt-4">
                                                {step.type !== "Action" && (
                                                    <div className="prose dark:prose-invert max-w-none">
                                                        <ReactMarkdown
                                                            remarkPlugins={[remarkGfm]}
                                                            rehypePlugins={[rehypeRaw]}
                                                            components={{
                                                                table: (props) => <div className="overflow-x-auto my-6"><table {...props} className="w-full border-collapse border border-border text-sm" /></div>,
                                                                p: (props) => <p {...props} className="mb-4 last:mb-0" />,
                                                                strong: (props) => <strong {...props} className="text-primary font-bold" />,
                                                            }}
                                                        >
                                                            {step.content}
                                                        </ReactMarkdown>
                                                    </div>
                                                )}

                                                {/* Options / Structured Result / Attachments */}
                                                <div className={cn(step.type !== "Action" && "mt-6")}>
                                                    {/* Structured Result Visualization */}
                                                    {step.type === "Action" && !step.attachment && (
                                                        <ResultCard type="Action" content={step.content} />
                                                    )}

                                                    {/* Existing Attachments */}
                                                    {step.attachment && step.attachment.type === "options" && (
                                                        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                                                            {(step.attachment as any).data.map((opt: any, idx: number) => (
                                                                <button
                                                                    key={idx}
                                                                    onClick={() => onOptionSelect && onOptionSelect(opt.value)}
                                                                    className="px-4 py-3 text-left glass-pane hover:bg-white/10 rounded-xl text-sm text-slate-100 transition-all flex items-center gap-3 group/btn"
                                                                >
                                                                    <div className="w-2 h-2 rounded-full bg-primary/40 group-hover/btn:bg-primary shadow-[0_0_8px_rgba(168,85,247,0.5)]" />
                                                                    <span className="font-medium">{opt.label}</span>
                                                                </button>
                                                            ))}
                                                        </div>
                                                    )}

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
                                    )}
                                </AnimatePresence>

                                {isCollapsed && (
                                    <p className="text-xs text-slate-500 italic mt-2">Reasoning hidden to streamline view...</p>
                                )}
                            </div>
                        </motion.div>
                    );
                })}
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
        setSaveStatus("Saving capability removed");
        setTimeout(() => setSaveStatus(null), 3000);
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

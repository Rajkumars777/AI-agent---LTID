"use client";

import { motion } from "framer-motion";
import { Bot, Activity, Play, CheckCircle2, Clock } from "lucide-react";
import { cn } from "@/lib/utils";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import rehypeRaw from "rehype-raw";

export type Step = {
    type: "Reasoning" | "Decision" | "Action";
    content: string;
    timestamp: string;
};

interface TimelineFeedProps {
    steps: Step[];
}

export function TimelineFeed({ steps }: TimelineFeedProps) {
    if (steps.length === 0) return null;

    return (
        <div className="w-full mx-auto mt-12 px-4 relative">
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
                                    }}
                                >
                                    {step.content}
                                </ReactMarkdown>
                            </div>
                        </div>
                    </motion.div>
                ))}
            </div>
        </div>
    );
}

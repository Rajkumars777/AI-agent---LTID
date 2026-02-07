"use client";

import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Send, Command, Sparkles } from "lucide-react";
import { cn } from "@/lib/utils";

interface InputConsoleProps {
    onSend: (message: string) => void;
    loading: boolean;
}

export function InputConsole({ onSend, loading }: InputConsoleProps) {
    const [input, setInput] = useState("");
    const [isFocused, setIsFocused] = useState(false);

    const handleSubmit = (e?: React.FormEvent) => {
        e?.preventDefault();
        if (!input.trim() || loading) return;
        onSend(input);
        setInput("");
    };

    return (
        <div className="w-full max-w-3xl mx-auto relative z-50">
            {/* Glow Effect */}
            <div
                className={cn(
                    "absolute -inset-1 bg-gradient-to-r from-primary via-purple-500 to-primary rounded-2xl blur-xl opacity-0 transition-opacity duration-500",
                    (isFocused || input.length > 0) && "opacity-30"
                )}
            />

            <motion.form
                onSubmit={handleSubmit}
                className={cn(
                    "relative flex items-center gap-3 p-3 rounded-2xl border transition-all duration-300",
                    "bg-white/[0.03] backdrop-blur-2xl shadow-2xl", // darker, more premium glass
                    isFocused
                        ? "border-indigo-500/50 shadow-[0_0_30px_-5px_oklch(0.6_0.2_280/0.3)]"
                        : "border-white/10 hover:border-white/20"
                )}
                initial={{ y: 20, opacity: 0 }}
                animate={{ y: 0, opacity: 1 }}
                transition={{ delay: 0.6 }}
            >
                <div className={cn(
                    "pl-3 transition-colors duration-300",
                    isFocused ? "text-indigo-400" : "text-slate-500"
                )}>
                    <Command className="w-6 h-6" />
                </div>

                <input
                    type="text"
                    value={input}
                    onChange={(e) => setInput(e.target.value)}
                    onFocus={() => setIsFocused(true)}
                    onBlur={() => setIsFocused(false)}
                    placeholder="Ask the agent to do something..."
                    className="flex-1 bg-transparent border-none outline-none text-lg placeholder:text-slate-500 py-2 text-slate-100 font-light tracking-wide"
                />

                <div className="pr-1 flex items-center gap-2">
                    <AnimatePresence>
                        {(input.length > 0 || loading) && (
                            <motion.button
                                initial={{ scale: 0.8, opacity: 0, filter: "blur(10px)" }}
                                animate={{ scale: 1, opacity: 1, filter: "blur(0px)" }}
                                exit={{ scale: 0.8, opacity: 0, filter: "blur(10px)" }}
                                type="submit"
                                disabled={loading}
                                className="p-2.5 rounded-xl bg-gradient-to-r from-indigo-500 to-purple-600 text-white hover:opacity-90 transition-all shadow-lg hover:shadow-indigo-500/25 active:scale-95"
                            >
                                {loading ? (
                                    <Sparkles className="w-5 h-5 animate-spin" />
                                ) : (
                                    <Send className="w-5 h-5" />
                                )}
                            </motion.button>
                        )}
                    </AnimatePresence>
                </div>
            </motion.form>
        </div>
    );
}

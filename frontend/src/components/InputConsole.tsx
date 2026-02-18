"use client";

import { useState, useRef, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Send, Command, Sparkles, Mic } from "lucide-react";
import { cn } from "@/lib/utils";

import { orchestrateWebTask, getApiBase } from "@/lib/api";

interface InputConsoleProps {
    onSend: (message: string) => void;
    loading: boolean;
    lastCommand?: string;  // For edit functionality
    onWebTaskComplete?: (result: any) => void;
}

export function InputConsole({ onSend, loading, lastCommand, onWebTaskComplete }: InputConsoleProps) {
    const [input, setInput] = useState("");
    const [isFocused, setIsFocused] = useState(false);
    const [isRecording, setIsRecording] = useState(false);
    const mediaRecorderRef = useRef<MediaRecorder | null>(null);
    const audioChunksRef = useRef<Blob[]>([]);
    const inputRef = useRef<HTMLInputElement>(null);

    // Web Orchestrator State - Removed local state for results
    // const [webStatus, setWebStatus] = useState("");
    // const [webResult, setWebResult] = useState<any>(null);
    // const [screenshotPath, setScreenshotPath] = useState<string | null>(null);
    const [showWebControls, setShowWebControls] = useState(false);

    // When lastCommand changes (user clicked Edit), populate input
    useEffect(() => {
        if (lastCommand && !loading) {
            setInput(lastCommand);
            inputRef.current?.focus();
        }
    }, [lastCommand, loading]);


    const handleSubmit = (e?: React.FormEvent) => {
        e?.preventDefault();
        if (!input.trim() || loading) return;
        onSend(input);
        setInput("");
        // setWebStatus(""); // Clear web status on new chat
        // setWebResult(null);
        // setScreenshotPath(null);
    };

    const startRecording = async () => {
        try {
            const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
            const mediaRecorder = new MediaRecorder(stream);
            mediaRecorderRef.current = mediaRecorder;
            audioChunksRef.current = [];

            mediaRecorder.ondataavailable = (event) => {
                if (event.data.size > 0) {
                    audioChunksRef.current.push(event.data);
                }
            };

            mediaRecorder.onstop = async () => {
                // Create audio blob
                const audioBlob = new Blob(audioChunksRef.current, { type: 'audio/wav' });

                // Send to backend for transcription
                await transcribeAudio(audioBlob);

                // Stop all tracks
                stream.getTracks().forEach(track => track.stop());
            };

            mediaRecorder.start();
            setIsRecording(true);

            // Auto-stop after 5 seconds (you can adjust this)
            setTimeout(() => {
                if (mediaRecorderRef.current?.state === 'recording') {
                    stopRecording();
                }
            }, 5000);

        } catch (error) {
            console.error('Microphone error:', error);
            alert('Could not access microphone. Please allow microphone permissions.');
        }
    };

    const stopRecording = () => {
        if (mediaRecorderRef.current && mediaRecorderRef.current.state === 'recording') {
            mediaRecorderRef.current.stop();
            setIsRecording(false);
        }
    };

    const transcribeAudio = async (audioBlob: Blob) => {
        try {
            const formData = new FormData();
            formData.append('file', audioBlob, 'voice_command.wav');

            const base = await getApiBase();
            const response = await fetch(`${base}/api/voice/transcribe`, {
                method: 'POST',
                body: formData,
            });

            if (!response.ok) {
                throw new Error('Transcription failed');
            }

            const data = await response.json();

            if (data.text) {
                // CRITICAL: Put text in input box, do NOT execute
                setInput(data.text);
            }

        } catch (error) {
            console.error('Transcription error:', error);
            alert('Voice transcription failed. Make sure the backend is running with Faster-Whisper installed.');
        }
    };

    const handleVoiceClick = () => {
        if (isRecording) {
            stopRecording();
        } else {
            startRecording();
        }
    };

    // --- Web Orchestrator Logic ---
    const sanitizeUrl = (input: string) => {
        let sanitized = input.trim();
        if (!sanitized) return "";
        // Fix common typos
        if (sanitized.startsWith("ttps://")) sanitized = "h" + sanitized;
        if (sanitized.startsWith("tp://")) sanitized = "ht" + sanitized;
        // Add schema if missing, but only if it looks like a domain
        if (!/^https?:\/\//i.test(sanitized) && sanitized.includes(".")) {
            sanitized = "https://" + sanitized;
        }
        return sanitized;
    };

    const runWebTask = async (action: string) => {
        const urlToCheck = input.trim();
        const targetUrl = sanitizeUrl(urlToCheck);

        if (!targetUrl) {
            // setWebStatus("⚠️ Please enter a URL above first.");
            if (onWebTaskComplete) onWebTaskComplete({ type: 'error', content: "⚠️ Please enter a URL above first." });
            return;
        }

        // If it's a manual scrape, update the input to reflect the sanitized URL
        if (targetUrl !== input) {
            setInput(targetUrl);
        }

        // setWebStatus(`🚀 Running ${action}...`);
        // setWebResult(null);
        // setScreenshotPath(null);

        try {
            const result = await orchestrateWebTask(targetUrl, action);

            if (onWebTaskComplete) {
                onWebTaskComplete({
                    type: "web_result",
                    data: result.data,
                    url: targetUrl,
                    screenshot: result.file,
                    status: result.status
                });
            }

        } catch (e) {
            // setWebStatus(`Error: ${e}`);
            if (onWebTaskComplete) onWebTaskComplete({ type: 'error', content: `Error: ${e}` });
        }
    };

    return (
        <div className="w-full max-w-3xl mx-auto relative z-50 flex flex-col gap-2">

            <div className="relative">
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
                        "bg-white/[0.03] backdrop-blur-2xl shadow-2xl",
                        isFocused
                            ? "border-indigo-500/50 shadow-[0_0_30px_-5px_oklch(0.6_0.2_280/0.3)]"
                            : "border-white/10 hover:border-white/20"
                    )}
                    initial={{ y: 20, opacity: 0 }}
                    animate={{ y: 0, opacity: 1 }}
                    transition={{ delay: 0.6 }}
                >
                    <div className={cn(
                        "pl-3 transition-colors duration-300 cursor-pointer",
                        isFocused || showWebControls ? "text-indigo-400" : "text-slate-500"
                    )}
                        onClick={() => setShowWebControls(!showWebControls)}
                        title="Toggle Web Tools"
                    >
                        <Command className="w-6 h-6" />
                    </div>

                    <input
                        ref={inputRef}
                        type="text"
                        value={input}
                        onChange={(e) => setInput(e.target.value)}
                        onFocus={() => setIsFocused(true)}
                        onBlur={() => setIsFocused(false)}
                        placeholder={isRecording ? "🎤 Listening..." : "Ask agent or enter URL for web tools..."}
                        className="flex-1 bg-transparent border-none outline-none text-lg placeholder:text-slate-500 py-2 text-slate-100 font-light tracking-wide"
                    />

                    <div className="pr-1 flex items-center gap-2">
                        {/* Voice Button */}
                        <button
                            type="button"
                            onClick={handleVoiceClick}
                            className={cn(
                                "w-10 h-10 rounded-full flex items-center justify-center transition-all duration-200 relative",
                                isRecording
                                    ? "bg-red-500 hover:bg-red-600 animate-pulse"
                                    : "bg-blue-500 hover:bg-blue-600"
                            )}
                            title={isRecording ? "Click to stop recording" : "Click to speak"}
                        >
                            <Mic className="w-5 h-5 text-white" />
                            {isRecording && (
                                <span className="absolute -top-1 -right-1 w-3 h-3 bg-red-600 rounded-full animate-ping" />
                            )}
                        </button>

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

            {/* Helper Text */}
            {isRecording && (
                <motion.div
                    initial={{ opacity: 0, y: -10 }}
                    animate={{ opacity: 1, y: 0 }}
                    className="text-center mt-2 text-sm text-red-400"
                >
                    🎤 Recording... Speak now (auto-stops in 5s or click mic)
                </motion.div>
            )}

            {/* Web Orchestrator Toolbar - Visible if toggled or if input looks like a URL */}
            <AnimatePresence>
                {(showWebControls || input.startsWith("http") || input.startsWith("www")) && (
                    <motion.div
                        initial={{ opacity: 0, height: 0 }}
                        animate={{ opacity: 1, height: "auto" }}
                        exit={{ opacity: 0, height: 0 }}
                        className="overflow-hidden"
                    >
                        <div className="flex gap-2 p-2 bg-black/40 backdrop-blur-md rounded-xl border border-white/5">
                            <button onClick={() => runWebTask("scrape_table")} className="flex-1 btn-xs bg-blue-600/20 hover:bg-blue-600/40 text-blue-400 py-2 rounded-lg text-xs font-medium border border-blue-500/30 transition-all">
                                📊 Scrape Table
                            </button>
                            <button onClick={() => runWebTask("read_page")} className="flex-1 btn-xs bg-purple-600/20 hover:bg-purple-600/40 text-purple-400 py-2 rounded-lg text-xs font-medium border border-purple-500/30 transition-all">
                                📖 Read Page
                            </button>
                            <button onClick={() => runWebTask("download_file")} className="flex-1 btn-xs bg-green-600/20 hover:bg-green-600/40 text-green-400 py-2 rounded-lg text-xs font-medium border border-green-500/30 transition-all">
                                ⬇️ Download
                            </button>
                        </div>
                    </motion.div>
                )}
            </AnimatePresence>



        </div>
    );
}

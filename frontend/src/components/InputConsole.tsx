"use client";

import { useState, useRef, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Send, Command, Sparkles, Mic } from "lucide-react";
import { cn } from "@/lib/utils";

import { getApiBase } from "@/lib/api";

interface InputConsoleProps {
    onSend: (message: string) => void;
    loading: boolean;
    lastCommand?: string;  // For edit functionality
}

export function InputConsole({ onSend, loading, lastCommand }: InputConsoleProps) {
    const [input, setInput] = useState("");
    const [isFocused, setIsFocused] = useState(false);
    const [isRecording, setIsRecording] = useState(false);
    const mediaRecorderRef = useRef<MediaRecorder | null>(null);
    const audioChunksRef = useRef<Blob[]>([]);
    const inputRef = useRef<HTMLInputElement>(null);



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



    return (
        <div className="w-full max-w-4xl mx-auto relative z-[60] flex flex-col gap-4">
            <div className="relative">
                {/* Ambient Glow behind the bar */}
                <div
                    className={cn(
                        "absolute -inset-4 bg-primary/20 rounded-[2.5rem] blur-3xl opacity-0 transition-all duration-1000 -z-10",
                        (isFocused || input.length > 0) && "opacity-100 scale-105"
                    )}
                />

                <motion.form
                    onSubmit={handleSubmit}
                    className={cn(
                        "relative flex items-center gap-4 p-2 rounded-[2rem] border transition-all duration-500",
                        "glass-pane",
                        isFocused
                            ? "border-primary/50 shadow-[0_0_40px_-10px_oklch(0.68_0.28_280/0.4)] scale-[1.01]"
                            : "border-border hover:border-border/80"
                    )}
                    initial={{ y: 30, opacity: 0 }}
                    animate={{ y: 0, opacity: 1 }}
                    transition={{ delay: 0.8, type: "spring", stiffness: 100 }}
                >
                    {/* Visual Anchor / Icon */}
                    <div className={cn(
                        "ml-3 p-3 rounded-full transition-all duration-500",
                        isFocused
                            ? "bg-primary/20 text-primary scale-110 rotate-12"
                            : "bg-secondary text-muted-foreground"
                    )}>
                        <Command className="w-6 h-6" />
                    </div>

                    <input
                        ref={inputRef}
                        type="text"
                        value={input}
                        onChange={(e) => setInput(e.target.value)}
                        onFocus={() => setIsFocused(true)}
                        onBlur={() => setIsFocused(false)}
                        placeholder={isRecording ? "🎤 Listening to your command..." : "Ask NEXUS to do anything..."}
                        className="flex-1 bg-transparent border-none outline-none text-xl placeholder:text-muted-foreground/50 py-4 text-foreground font-light tracking-wide outline-none focus:ring-0"
                    />

                    <div className="mr-2 flex items-center gap-3">
                        {/* Voice Button */}
                        <button
                            type="button"
                            onClick={handleVoiceClick}
                            className={cn(
                                "w-12 h-12 rounded-full flex items-center justify-center transition-all duration-300 relative group overflow-hidden",
                                isRecording
                                    ? "bg-red-500 animate-pulse"
                                    : "bg-secondary hover:bg-blue-500/20 text-muted-foreground hover:text-blue-500"
                            )}
                            title={isRecording ? "Click to stop recording" : "Click to speak"}
                        >
                            <Mic className={cn("w-6 h-6 transition-transform duration-300", !isRecording && "group-hover:scale-110")} />
                            {isRecording && (
                                <span className="absolute inset-0 bg-red-600 rounded-full animate-ping opacity-20" />
                            )}
                        </button>

                        <AnimatePresence>
                            {(input.length > 0 || loading) && (
                                <motion.button
                                    initial={{ scale: 0.5, opacity: 0, x: 20 }}
                                    animate={{ scale: 1, opacity: 1, x: 0 }}
                                    exit={{ scale: 0.5, opacity: 0, x: 20 }}
                                    type="submit"
                                    disabled={loading}
                                    className="h-12 px-6 rounded-2xl bg-primary text-primary-foreground font-bold transition-all shadow-[0_10px_20px_-5px_oklch(0.68_0.28_280/0.3)] hover:shadow-[0_15px_30px_-5px_oklch(0.68_0.28_280/0.5)] hover:-translate-y-0.5 active:translate-y-0 active:scale-95 flex items-center gap-2 group"
                                >
                                    {loading ? (
                                        <Sparkles className="w-5 h-5 animate-spin" />
                                    ) : (
                                        <>
                                            <span className="text-sm tracking-widest uppercase font-black">Send</span>
                                            <Send className="w-4 h-4 transition-transform duration-300 group-hover:translate-x-1 group-hover:-translate-y-1" />
                                        </>
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





        </div>
    );
}

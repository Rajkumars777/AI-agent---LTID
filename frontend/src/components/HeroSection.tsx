"use client";

import { motion } from "framer-motion";

export function HeroSection() {
    return (
        <div className="relative flex flex-col items-center justify-center py-20 text-center z-10 overflow-visible">
            {/* Ambient Background Glow */}
            <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[400px] bg-primary/20 blur-[120px] rounded-full pointer-events-none -z-10 animate-pulse" />

            <motion.h1
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 1.2, delay: 0.2, type: "spring", bounce: 0.4 }}
                className="text-7xl md:text-9xl font-black tracking-[0.05em] mb-10 leading-none"
            >
                <span className="text-foreground drop-shadow-[0_0_30px_rgba(255,255,255,0.1)] dark:drop-shadow-[0_0_30px_rgba(255,255,255,0.3)] filter">
                    NEXUS
                </span>{" "}
                <br />
                <span className="relative inline-block mt-4">
                    <span className="absolute -inset-4 transform -skew-x-12 bg-gradient-to-r from-indigo-500 via-purple-500 to-pink-500 opacity-20 blur-3xl rounded-full" />
                    <span className="relative bg-clip-text text-transparent bg-gradient-to-r from-indigo-600 via-purple-600 to-pink-600 dark:from-indigo-400 dark:via-purple-400 dark:to-pink-400 animate-gradient-x bg-300% text-5xl md:text-6xl font-bold tracking-widest uppercase italic">
                        Next-Gen AI Agent
                    </span>
                </span>
            </motion.h1>

            <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.8, delay: 0.6 }}
                className="relative"
            >
                <p className="text-lg md:text-xl text-muted-foreground max-w-2xl leading-relaxed font-light tracking-wide">
                    Experience the power of an intelligent <span className="text-primary font-medium">workflow automation</span> system.
                    <br />
                    <span className="text-sm text-muted-foreground/60 mt-2 block italic">Powered by advanced autonomous reasoning</span>
                </p>
                <div className="mt-8 h-px w-24 mx-auto bg-gradient-to-r from-transparent via-primary/50 to-transparent" />
            </motion.div>
        </div>
    );
}

"use client";

import { motion } from "framer-motion";
import { Sparkles } from "lucide-react";

export function HeroSection() {
    return (
        <div className="relative flex flex-col items-center justify-center py-5 text-center z-10">


            <motion.h1
                initial={{ opacity: 0, scale: 0.9 }}
                animate={{ opacity: 1, scale: 1 }}
                transition={{ duration: 1, delay: 0.2, type: "spring" }}
                className="text-6xl md:text-8xl font-black tracking-tighter mb-8 leading-tight"
            >
                <span className="text-white drop-shadow-2xl filter">
                    NEXUS
                </span>{" "}
                <br />
                <span className="relative inline-block">
                    <span className="absolute -inset-2 transform -skew-x-6 bg-gradient-to-r from-indigo-500 via-purple-500 to-pink-500 opacity-20 blur-3xl rounded-full" />
                    <span className="relative bg-clip-text text-8xl text-transparent bg-gradient-to-r from-indigo-400 via-purple-400 to-pink-400 animate-gradient-x bg-300%">
                        Next-Gen AI Agent
                    </span>
                </span>
            </motion.h1>

            <motion.p
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.8, delay: 0.4 }}
                className="text-xl md:text-xl text-slate-400 max-w-2xl leading-relaxed font-light"
            >
                Experience the power of an intelligent workflow automation system.
            </motion.p>
        </div >
    );
}

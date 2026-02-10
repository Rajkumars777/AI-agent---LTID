"use client";

import { useState, useCallback } from "react";
import { HeroSection } from "@/components/HeroSection";
import { InputConsole } from "@/components/InputConsole";
import { TimelineFeed, Step } from "@/components/TimelineFeed";
import { RecentsHistory } from "@/components/RecentsHistory";
import { chatWithAgent, cancelOperation, generateTaskId } from "@/lib/api";
import { motion, AnimatePresence } from "framer-motion";
import { StopCircle, Edit3, RotateCcw } from "lucide-react";

export default function Dashboard() {
  const [steps, setSteps] = useState<Step[]>([]);
  const [loading, setLoading] = useState(false);
  const [history, setHistory] = useState<string[]>([]);
  const [lastCommand, setLastCommand] = useState<string>("");
  const [cancelled, setCancelled] = useState(false);

  // Handle cancel operation
  const handleCancel = useCallback(async () => {
    setCancelled(true);
    await cancelOperation();
    setLoading(false);
    setSteps([{
      type: "Action",
      content: "⏹️ Operation cancelled by user",
      timestamp: new Date().toLocaleTimeString()
    }]);
  }, []);

  // Handle edit/retry with modification
  const handleEdit = useCallback(() => {
    // This will be handled by InputConsole - we just need to pass lastCommand
    setCancelled(false);
  }, []);

  // Keep track of the latest agent thought process
  const handleSend = async (input: string) => {
    if (!input.trim()) return;

    setLoading(true);
    setSteps([]);
    setCancelled(false);
    setLastCommand(input);

    // Add to specific history (prevent duplicates at top)
    setHistory(prev => {
      const newHist = [input, ...prev.filter(h => h !== input)];
      return newHist.slice(0, 10); // Keep last 10
    });

    try {
      const taskId = generateTaskId();
      const res = await chatWithAgent(input, taskId);

      if (res.cancelled) {
        setSteps([{
          type: "Action",
          content: "⏹️ Operation cancelled",
          timestamp: new Date().toLocaleTimeString()
        }]);
      } else if (res.steps) {
        setSteps(res.steps);
      } else {
        setSteps([{
          type: "Action",
          content: "Task executed successfully. (Backend returned no detailed steps)",
          timestamp: new Date().toLocaleTimeString()
        }]);
      }
    } catch (e) {
      if (!cancelled) {
        setSteps([{
          type: "Action",
          content: "System Error: " + e,
          timestamp: new Date().toLocaleTimeString()
        }]);
      }
    }
    setLoading(false);
  };

  return (
    <main className="min-h-screen bg-[#050510] relative overflow-hidden font-sans selection:bg-purple-500/30 flex flex-col">
      {/* Background Gradients */}
      <div className="fixed inset-0 pointer-events-none">
        <div className="absolute top-[-10%] left-[-10%] w-[40%] h-[40%] bg-purple-500/10 rounded-full blur-[120px] animate-pulse" />
        <div className="absolute bottom-[-10%] right-[-10%] w-[40%] h-[40%] bg-blue-500/10 rounded-full blur-[120px] animate-pulse delay-1000" />
      </div>

      {/* Top Section: Hero + Input */}
      <div className="relative w-full max-w-[95%] mx-auto pt-12 pb-8 flex flex-col items-center z-10">
        <HeroSection />
        <div className="w-full max-w-4xl mt-8">
          <InputConsole
            onSend={handleSend}
            loading={loading}
            lastCommand={lastCommand}
          />

          {/* Stop/Edit Controls - Show when loading or after cancel */}
          <AnimatePresence>
            {loading && (
              <motion.div
                initial={{ opacity: 0, y: -10 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -10 }}
                className="flex justify-center gap-4 mt-4"
              >
                <button
                  onClick={handleCancel}
                  className="flex items-center gap-2 px-6 py-3 bg-red-500/20 hover:bg-red-500/40 border border-red-500/50 rounded-xl text-red-400 font-medium transition-all duration-200 hover:scale-105"
                >
                  <StopCircle className="w-5 h-5" />
                  Stop Operation
                </button>
              </motion.div>
            )}
          </AnimatePresence>

          {/* After cancellation - show edit/retry options */}
          <AnimatePresence>
            {cancelled && !loading && lastCommand && (
              <motion.div
                initial={{ opacity: 0, y: -10 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -10 }}
                className="flex justify-center gap-4 mt-4"
              >
                <button
                  onClick={() => handleSend(lastCommand)}
                  className="flex items-center gap-2 px-5 py-2.5 bg-blue-500/20 hover:bg-blue-500/40 border border-blue-500/50 rounded-xl text-blue-400 font-medium transition-all duration-200 hover:scale-105"
                >
                  <RotateCcw className="w-4 h-4" />
                  Retry
                </button>
                <button
                  onClick={handleEdit}
                  className="flex items-center gap-2 px-5 py-2.5 bg-purple-500/20 hover:bg-purple-500/40 border border-purple-500/50 rounded-xl text-purple-400 font-medium transition-all duration-200 hover:scale-105"
                >
                  <Edit3 className="w-4 h-4" />
                  Edit Command
                </button>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </div>

      {/* Main Content Area: Flex Row */}
      <div className="flex-1 w-full max-w-[98%] mx-auto flex border-t border-white/5 min-h-0">

        {/* Left: Action Feed (80%) */}
        <div className="w-[80%] relative overflow-y-auto custom-scrollbar border-r border-white/5">
          <TimelineFeed steps={steps} onOptionSelect={handleSend} />
        </div>

        {/* Right: Recents (20%) */}
        <div className="w-[20%] hidden lg:block overflow-y-auto custom-scrollbar">
          <RecentsHistory recents={history} onSelect={(cmd) => handleSend(cmd)} />
        </div>

      </div>
    </main>
  );
}

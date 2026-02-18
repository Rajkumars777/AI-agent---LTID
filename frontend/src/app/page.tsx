"use client";

import { useState, useCallback } from "react";
import { HeroSection } from "@/components/HeroSection";
import { InputConsole } from "@/components/InputConsole";
import { TimelineFeed, Step } from "@/components/TimelineFeed";
import { RecentsHistory } from "@/components/RecentsHistory";
import BrowserViewport from "@/components/BrowserViewport";

import { chatWithAgent, cancelOperation, generateTaskId } from "@/lib/api";
import { motion, AnimatePresence } from "framer-motion";
import { StopCircle, Edit3, RotateCcw, Globe } from "lucide-react";

export default function Dashboard() {
  const [steps, setSteps] = useState<Step[]>([]);
  const [loading, setLoading] = useState(false);
  const [history, setHistory] = useState<string[]>([]);
  const [lastCommand, setLastCommand] = useState<string>("");
  const [cancelled, setCancelled] = useState(false);
  const [isBrowserMode, setIsBrowserMode] = useState(false);
  const [browserUrl, setBrowserUrl] = useState("https://google.com");
  const [isHistoryOpen, setIsHistoryOpen] = useState(false);

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
      return newHist.slice(0, 50); // Keep last 50
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

  const handleWebTaskComplete = (result: any) => {
    const newStep: Step = {
      type: "Action",
      content: `**Web Task Completed**: ${result.status}`,
      timestamp: new Date().toLocaleTimeString(),
      attachment: {
        type: "web_result",
        data: result.data,
        url: result.url,
        screenshot: result.screenshot
      }
    };
    setSteps(prev => [...prev, newStep]);
  };

  const toggleBrowserMode = async () => {
    const newMode = !isBrowserMode;
    setIsBrowserMode(newMode);
    // When turning browser mode OFF, hide the Tauri browser view (if running in Tauri)
    if (!newMode) {
      if (typeof window !== "undefined" && (window as any).__TAURI__) {
        try {
          const { invoke } = await import("@tauri-apps/api/core");
          await invoke("hide_browser_view", { visible: false });
        } catch {
          // In web/dev mode this import or invoke may fail; ignore silently
        }
      }
    }
  };

  return (
    <main className="min-h-screen bg-[#050510] relative overflow-hidden font-sans selection:bg-purple-500/30 flex flex-col">
      {/* Background Gradients */}
      <div className="fixed inset-0 pointer-events-none">
        <div className="absolute top-[-10%] left-[-10%] w-[40%] h-[40%] bg-purple-500/10 rounded-full blur-[120px] animate-pulse" />
        <div className="absolute bottom-[-10%] right-[-10%] w-[40%] h-[40%] bg-blue-500/10 rounded-full blur-[120px] animate-pulse delay-1000" />
      </div>

      {/* Floating Controls */}
      {/* 1. Top Left: Browser Mode Toggle */}
      <div className="fixed top-6 left-6 z-50">
        <button
          onClick={toggleBrowserMode}
          className={`flex items-center gap-2 px-4 py-2 rounded-lg font-medium transition-all shadow-lg backdrop-blur-md ${isBrowserMode
            ? "bg-emerald-500/20 text-emerald-400 border border-emerald-500/50"
            : "bg-white/5 text-slate-400 border border-white/10 hover:bg-white/10"
            }`}
        >
          <Globe className="w-4 h-4" />
          {isBrowserMode ? "Browser Active" : "Browser Mode"}
        </button>
      </div>

      {/* 2. Top Right: History Toggle */}
      <div className="fixed top-6 right-6 z-50">
        <button
          onClick={() => setIsHistoryOpen(true)}
          className="p-3 rounded-full bg-white/5 hover:bg-white/10 border border-white/10 text-slate-400 transition-all hover:scale-105 shadow-lg backdrop-blur-md"
        >
          <RotateCcw className="w-5 h-5" />
        </button>
      </div>

      {/* Top Section: Hero + Input */}
      <div className="relative w-full max-w-[95%] mx-auto pt-12 pb-8 flex flex-col items-center z-10">
        <HeroSection />
        <div className="w-full max-w-4xl mt-8">
          <InputConsole
            onSend={handleSend}
            loading={loading}
            lastCommand={lastCommand}
            onWebTaskComplete={handleWebTaskComplete}
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

      {/* Main Content Area: Full Width */}
      <div className="flex-1 w-full max-w-[95%] mx-auto flex border-t border-white/5 min-h-0">
        {/* Results Area (Full Width) */}
        <div className="w-full relative overflow-y-auto custom-scrollbar">
          {isBrowserMode ? (
            <BrowserViewport url={browserUrl} isModalOpen={false} />
          ) : (
            <TimelineFeed steps={steps} onOptionSelect={handleSend} />
          )}
        </div>
      </div>

      {/* History Sidebar Drawer */}
      <AnimatePresence>
        {isHistoryOpen && (
          <>
            {/* Backdrop */}
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              onClick={() => setIsHistoryOpen(false)}
              className="fixed inset-0 bg-black/60 backdrop-blur-sm z-[100]"
            />
            {/* Drawer */}
            <motion.div
              initial={{ x: "100%" }}
              animate={{ x: 0 }}
              exit={{ x: "100%" }}
              transition={{ type: "spring", damping: 25, stiffness: 200 }}
              className="fixed top-0 right-0 bottom-0 w-80 bg-[#0A0A12] border-l border-white/10 z-[101] shadow-2xl"
            >
              <div className="h-full flex flex-col">
                {/* Drawer Header */}
                <div className="p-4 border-b border-white/5 flex items-center justify-between">
                  <h2 className="text-sm font-semibold text-slate-200 uppercase tracking-wider">History</h2>
                  <button
                    onClick={() => setIsHistoryOpen(false)}
                    className="p-1 hover:bg-white/10 rounded-md transition-colors"
                  >
                    <RotateCcw className="w-4 h-4 text-slate-500 rotate-45" /> {/* Using rotate as close icon substitute for now */}
                  </button>
                </div>

                {/* Drawer Content */}
                <div className="flex-1 overflow-y-auto custom-scrollbar">
                  <RecentsHistory
                    recents={history}
                    onSelect={(cmd) => {
                      handleSend(cmd);
                      setIsHistoryOpen(false);
                    }}
                  // TODO: Add onDelete and onFolderMove handlers here in next step
                  />
                </div>
              </div>
            </motion.div>
          </>
        )}
      </AnimatePresence>

    </main>
  );
}

"use client";

import { useState, useCallback, useEffect } from "react";
import { HeroSection } from "@/components/HeroSection";
import { InputConsole } from "@/components/InputConsole";
import { TimelineFeed, Step } from "@/components/TimelineFeed";
import { RecentsHistory } from "@/components/RecentsHistory";
import BrowserViewport from "@/components/BrowserViewport";

import { chatWithAgent, cancelOperation, generateTaskId, resumeTask } from "@/lib/api";
import { useWebsocket, WebSocketEvent } from "@/hooks/useWebsocket";
import { motion, AnimatePresence } from "framer-motion";
import { StopCircle, Edit3, RotateCcw, Globe, Sun, Moon } from "lucide-react";
import { cn } from "@/lib/utils";

export default function Dashboard() {
  const [steps, setSteps] = useState<Step[]>([]);
  const [loading, setLoading] = useState(false);
  const [history, setHistory] = useState<string[]>([]);
  const [lastCommand, setLastCommand] = useState<string>("");
  const [cancelled, setCancelled] = useState(false);
  const [isAssistantMode, setIsAssistantMode] = useState(false);
  const [isHistoryOpen, setIsHistoryOpen] = useState(false);
  const [isDark, setIsDark] = useState(true);
  const [activeTaskId, setActiveTaskId] = useState<string | null>(null);

  // Sync theme with document class
  useEffect(() => {
    if (isDark) {
      document.documentElement.classList.add("dark");
    } else {
      document.documentElement.classList.remove("dark");
    }
  }, [isDark]);

  // Handle real-time events from WebSocket
  const handleWebSocketEvent = useCallback((event: WebSocketEvent) => {
    const { type, data } = event;
    const timestamp = new Date().toLocaleTimeString();

    setSteps(prev => {
      // 1. Map thinking/analysis
      if (type === "Thinking" || type === "NLU_Success") {
        const content = type === "Thinking" ? data.message : "NLU Analysis complete.";
        // Avoid duplicate identical thinking blocks
        if (prev.length > 0 && prev[prev.length - 1].content === content) return prev;
        return [...prev, { type: "Reasoning", content, timestamp }];
      }

      // 2. Map Screen Agent actions
      if (type === "AgentStep" || type === "ActionStarted" || type === "ScreenTaskStarted") {
        const content = data.desc || data.action || data.task || "Executing action...";
        return [...prev, { type: "Action", content, timestamp }];
      }

      // 3. Map Results
      if (type === "ActionResult" || type === "AgentStepDone" || type === "AgentDone") {
        const content = data.result || data.message || "Action completed.";
        // Update the last "Action" step with result if possible, or add new
        if (prev.length > 0 && prev[prev.length - 1].type === "Action") {
          const last = prev[prev.length - 1];
          return [...prev.slice(0, -1), { ...last, content: `${last.content}\n\n${content}` }];
        }
        return [...prev, { type: "Decision", content, timestamp }];
      }

      // 4. Handle Questions (Interactive)
      if (type === "AgentQuestion" || type === "REQUIRE_HELP") {
        return [...prev, {
          type: "Decision",
          content: data.prompt || data.question,
          timestamp,
          attachment: { type: "options", data: [{ label: "Reply to Agent", value: "REPLY_TRIGGER" }] }
        }];
      }

      return prev;
    });
  }, []);

  useWebsocket(activeTaskId, handleWebSocketEvent);

  // Handle cancel operation
  const handleCancel = useCallback(async () => {
    setCancelled(true);
    await cancelOperation();
    setLoading(false);
    setActiveTaskId(null);
    setSteps(prev => [...prev, {
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
      setActiveTaskId(taskId);

      const res = await chatWithAgent(input, taskId);

      if (res.cancelled) {
        // Handled by handleCancel usually, but for completeness:
        if (!cancelled) {
          setSteps(prev => [...prev, {
            type: "Action",
            content: "⏹️ Operation cancelled",
            timestamp: new Date().toLocaleTimeString()
          }]);
        }
      } else if (res.steps && res.steps.length > 0) {
        // If WebSocket didn't populate steps (e.g. fast task), use the response
        setSteps(prev => prev.length === 0 ? res.steps : prev);
      }
    } catch (e) {
      if (!cancelled) {
        setSteps(prev => [...prev, {
          type: "Action",
          content: "System Error: " + e,
          timestamp: new Date().toLocaleTimeString()
        }]);
      }
    } finally {
      setLoading(false);
      // We keep activeTaskId for a moment to catch final events, but can clear it
      setTimeout(() => setActiveTaskId(null), 2000);
    }
  };

  // Handle clicking options in the timeline (like "Reply to Agent")
  const handleOptionSelect = async (value: string) => {
    if (value === "REPLY_TRIGGER") {
      const reply = window.prompt("Nexus requires additional information to continue:");
      if (reply && activeTaskId) {
        setLoading(true);
        try {
          await resumeTask(activeTaskId, reply);
          // The agent will resume and emit events via WebSocket
        } catch (e) {
          console.error("Resume failed", e);
        } finally {
          setLoading(false);
        }
      }
    } else {
      handleSend(value);
    }
  };



  return (
    <main className="min-h-screen bg-background relative font-sans selection:bg-primary/30 flex flex-col">
      {/* Dynamic Background Elements */}
      <div className="fixed inset-0 pointer-events-none z-0">
        <div className="absolute top-[-20%] left-[-10%] w-[60%] h-[60%] bg-primary/10 rounded-full blur-[160px] animate-pulse" />
        <div className="absolute bottom-[-10%] right-[-10%] w-[50%] h-[50%] bg-blue-600/10 rounded-full blur-[140px] animate-pulse delay-1000" />
      </div>

      {/* Floating Controls */}
      <div className="fixed top-8 left-8 right-8 flex justify-between items-center z-[100] pointer-events-none">

        {/* Assistant Mode Button (Left) */}
        <div className="pointer-events-auto">
          <button
            onClick={() => setIsAssistantMode(!isAssistantMode)}
            className={cn(
              "flex items-center gap-2.5 px-5 py-2.5 rounded-2xl font-bold text-xs uppercase tracking-widest transition-all shadow-2xl backdrop-blur-xl border",
              isAssistantMode
                ? "bg-blue-500/20 text-blue-500 dark:text-blue-400 border-blue-500/50 shadow-blue-500/20"
                : "bg-secondary text-muted-foreground border-border hover:bg-secondary/80 hover:border-border/80"
            )}
          >
            <div className={cn("w-2 h-2 rounded-full", isAssistantMode ? "bg-blue-400 animate-pulse" : "bg-slate-400")} />
            {isAssistantMode ? "Assistant Active" : "Assistant Mode"}
          </button>
        </div>

        <div className="flex gap-4 pointer-events-auto">
          {/* Theme Toggle */}
          <button
            onClick={() => setIsDark(!isDark)}
            className="p-3.5 rounded-2xl bg-white/5 hover:bg-white/10 border border-white/10 text-slate-400 transition-all hover:scale-110 shadow-2xl backdrop-blur-xl group relative overflow-hidden"
          >
            <AnimatePresence mode="wait">
              {isDark ? (
                <motion.div
                  key="moon"
                  initial={{ y: 20, opacity: 0, rotate: 45 }}
                  animate={{ y: 0, opacity: 1, rotate: 0 }}
                  exit={{ y: -20, opacity: 0, rotate: -45 }}
                  transition={{ duration: 0.3 }}
                >
                  <Moon className="w-5 h-5 text-blue-400" />
                </motion.div>
              ) : (
                <motion.div
                  key="sun"
                  initial={{ y: 20, opacity: 0, rotate: 45 }}
                  animate={{ y: 0, opacity: 1, rotate: 0 }}
                  exit={{ y: -20, opacity: 0, rotate: -45 }}
                  transition={{ duration: 0.3 }}
                >
                  <Sun className="w-5 h-5 text-amber-400" />
                </motion.div>
              )}
            </AnimatePresence>
          </button>

          <button
            onClick={() => setIsHistoryOpen(true)}
            className="p-3.5 rounded-2xl bg-secondary hover:bg-secondary/80 border border-border text-muted-foreground transition-all hover:scale-110 shadow-2xl backdrop-blur-xl group"
          >
            <RotateCcw className="w-5 h-5 group-hover:rotate-[-45deg] transition-transform duration-300" />
          </button>
        </div>
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
        </div >
      </div >

      {/* Main Content Area */}
      <div className="w-full max-w-7xl mx-auto z-10 pb-32">
        <div className="w-full">
          <TimelineFeed steps={steps} onOptionSelect={handleOptionSelect} />
        </div>
      </div>
      {/* History Sidebar Drawer */}
      <AnimatePresence>
        {
          isHistoryOpen && (
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
                className="fixed top-0 right-0 bottom-0 w-80 bg-background border-l border-border z-[101] shadow-2xl"
              >
                <div className="h-full flex flex-col">
                  {/* Drawer Header */}
                  <div className="p-4 border-b border-border flex items-center justify-between">
                    <h2 className="text-sm font-semibold text-foreground uppercase tracking-wider">History</h2>
                    <button
                      onClick={() => setIsHistoryOpen(false)}
                      className="p-1 hover:bg-secondary rounded-md transition-colors"
                    >
                      <RotateCcw className="w-4 h-4 text-muted-foreground rotate-45" /> {/* Using rotate as close icon substitute for now */}
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
          )
        }
      </AnimatePresence >

    </main >
  );
}

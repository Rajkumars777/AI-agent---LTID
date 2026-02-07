"use client";

import { useState } from "react";
import { HeroSection } from "@/components/HeroSection";
import { InputConsole } from "@/components/InputConsole";
import { TimelineFeed, Step } from "@/components/TimelineFeed";
import { RecentsHistory } from "@/components/RecentsHistory";
import { chatWithAgent } from "@/lib/api";

export default function Dashboard() {
  const [steps, setSteps] = useState<Step[]>([]);
  const [loading, setLoading] = useState(false);
  const [history, setHistory] = useState<string[]>([]);

  // Keep track of the latest agent thought process
  const handleSend = async (input: string) => {
    if (!input.trim()) return;

    setLoading(true);
    setSteps([]);

    // Add to specific history (prevent duplicates at top)
    setHistory(prev => {
      const newHist = [input, ...prev.filter(h => h !== input)];
      return newHist.slice(0, 10); // Keep last 10
    });

    try {
      const res = await chatWithAgent(input);
      if (res.steps) {
        setSteps(res.steps);
      } else {
        setSteps([{
          type: "Action",
          content: "Task executed successfully. (Backend returned no detailed steps)",
          timestamp: new Date().toLocaleTimeString()
        }]);
      }
    } catch (e) {
      setSteps([{
        type: "Action",
        content: "System Error: " + e,
        timestamp: new Date().toLocaleTimeString()
      }]);
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
          <InputConsole onSend={handleSend} loading={loading} />
        </div>
      </div>

      {/* Main Content Area: Flex Row */}
      <div className="flex-1 w-full max-w-[98%] mx-auto flex border-t border-white/5 min-h-0">

        {/* Left: Action Feed (80%) */}
        <div className="w-[80%] relative overflow-y-auto custom-scrollbar border-r border-white/5">
          <TimelineFeed steps={steps} />
        </div>

        {/* Right: Recents (20%) */}
        <div className="w-[20%] hidden lg:block overflow-y-auto custom-scrollbar">
          <RecentsHistory recents={history} onSelect={(cmd) => handleSend(cmd)} />
        </div>

      </div>
    </main>
  );
}

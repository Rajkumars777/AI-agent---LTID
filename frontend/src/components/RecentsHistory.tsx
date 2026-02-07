"use client";

import { Clock, ChevronRight } from "lucide-react";
import { cn } from "@/lib/utils";

interface RecentsHistoryProps {
    recents: string[];
    onSelect: (cmd: string) => void;
}

export function RecentsHistory({ recents, onSelect }: RecentsHistoryProps) {
    // Fallback if empty
    const list = recents.length > 0 ? recents : [
        "open sample.xls",
        "add row to sample.xls",
        "search for 'budget'",
    ];

    return (
        <div className="w-full h-full p-4 border-l border-white/5 bg-white/[0.02]">
            <div className="flex items-center gap-2 mb-4 text-slate-400">
                <Clock className="w-4 h-4" />
                <h3 className="text-sm font-semibold uppercase tracking-wider">Recents</h3>
            </div>

            <div className="space-y-2">
                {list.map((cmd, i) => (
                    <button
                        key={i}
                        onClick={() => onSelect(cmd)}
                        className="w-full text-left p-3 rounded-lg hover:bg-white/5 transition-colors group flex items-center justify-between"
                    >
                        <span className="text-sm text-slate-300 truncate font-light group-hover:text-white transition-colors">
                            {cmd}
                        </span>
                        <ChevronRight className="w-3 h-3 text-slate-600 group-hover:text-slate-400 opacity-0 group-hover:opacity-100 transition-all" />
                    </button>
                ))}
            </div>
        </div>
    );
}

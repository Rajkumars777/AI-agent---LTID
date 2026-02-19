import { useState } from "react";
import { Clock, ChevronRight, Trash2, Folder, FolderPlus, MoreHorizontal } from "lucide-react";
import { cn } from "@/lib/utils";
import { motion, AnimatePresence } from "framer-motion";

interface RecentsHistoryProps {
    recents: string[];
    onSelect: (cmd: string) => void;
}

interface FolderData {
    id: string;
    name: string;
    items: string[];
}

export function RecentsHistory({ recents, onSelect }: RecentsHistoryProps) {
    const [folders, setFolders] = useState<FolderData[]>([]);
    const [isCreatingFolder, setIsCreatingFolder] = useState(false);
    const [newFolderName, setNewFolderName] = useState("");
    // Local state to manage deleted items visually until parent updates
    const [deletedItems, setDeletedItems] = useState<string[]>([]);

    const visibleRecents = recents.filter(r => !deletedItems.includes(r));

    if (visibleRecents.length === 0 && folders.length === 0) {
        return (
            <div className="w-full h-full p-6 flex flex-col items-center justify-center text-slate-500 text-sm">
                <Clock className="w-8 h-8 mb-2 opacity-20" />
                <p>No history yet</p>
            </div>
        );
    }

    const handleDelete = (item: string, e: React.MouseEvent) => {
        e.stopPropagation();
        setDeletedItems(prev => [...prev, item]);
    };

    const handleCreateFolder = () => {
        if (!newFolderName.trim()) return;
        setFolders(prev => [...prev, {
            id: Date.now().toString(),
            name: newFolderName.trim(),
            items: []
        }]);
        setNewFolderName("");
        setIsCreatingFolder(false);
    };

    const addToFolder = (item: string, folderId: string, e: React.MouseEvent) => {
        e.stopPropagation();
        // Move item to folder
        setFolders(prev => prev.map(f => {
            if (f.id === folderId) {
                return { ...f, items: [...f.items, item] };
            }
            return f;
        }));
        setDeletedItems(prev => [...prev, item]); // Remove from main list
    };

    return (
        <div className="w-full h-full p-6 bg-transparent">
            <div className="flex items-center justify-between mb-8">
                <div className="flex items-center gap-3 text-muted-foreground">
                    <div className="p-2 rounded-xl bg-secondary border border-border">
                        <Clock className="w-4 h-4" />
                    </div>
                    <h3 className="text-sm font-black uppercase tracking-[0.2em] text-foreground/50">History</h3>
                </div>
                <button
                    onClick={() => setIsCreatingFolder(true)}
                    className="p-2 hover:bg-white/10 rounded-xl text-slate-500 hover:text-primary transition-all duration-300"
                    title="New Folder"
                >
                    <FolderPlus className="w-5 h-5" />
                </button>
            </div>

            {/* Folder Creation Input */}
            <AnimatePresence>
                {isCreatingFolder && (
                    <motion.div
                        initial={{ opacity: 0, y: -10 }}
                        animate={{ opacity: 1, y: 0 }}
                        exit={{ opacity: 0, y: -10 }}
                        className="mb-6 p-3 glass-pane rounded-2xl border-primary/20"
                    >
                        <input
                            type="text"
                            value={newFolderName}
                            onChange={(e) => setNewFolderName(e.target.value)}
                            placeholder="Folder name..."
                            className="w-full bg-transparent text-sm text-foreground outline-none placeholder:text-muted-foreground mb-3"
                            autoFocus
                            onKeyDown={(e) => e.key === 'Enter' && handleCreateFolder()}
                        />
                        <div className="flex justify-end gap-3">
                            <button onClick={() => setIsCreatingFolder(false)} className="text-[10px] font-bold uppercase tracking-widest text-muted-foreground hover:text-foreground transition-colors">Cancel</button>
                            <button onClick={handleCreateFolder} className="text-[10px] font-bold uppercase tracking-widest text-primary hover:text-primary/80 transition-colors">Create</button>
                        </div>
                    </motion.div>
                )}
            </AnimatePresence>

            <div className="space-y-6">
                {/* Folders List */}
                {folders.map(folder => (
                    <div key={folder.id} className="group">
                        <div className="flex items-center gap-3 text-foreground p-3 rounded-2xl hover:bg-secondary border border-transparent hover:border-border transition-all duration-300 cursor-pointer">
                            <div className="p-2 bg-amber-500/10 rounded-xl">
                                <Folder className="w-4 h-4 text-amber-500" />
                            </div>
                            <span className="text-sm font-bold flex-1 tracking-tight">{folder.name}</span>
                            <span className="text-[10px] font-bold text-muted-foreground bg-secondary px-2 py-0.5 rounded-full">{folder.items.length}</span>
                        </div>
                        {folder.items.length > 0 && (
                            <div className="pl-6 mt-2 space-y-2 border-l-2 border-white/5 ml-5">
                                {folder.items.map((item, idx) => (
                                    <div key={idx} onClick={() => onSelect(item)} className="text-xs text-muted-foreground py-2 px-3 hover:bg-secondary rounded-xl cursor-pointer truncate transition-colors border border-transparent hover:border-border font-light">
                                        {item}
                                    </div>
                                ))}
                            </div>
                        )}
                    </div>
                ))}

                {/* Loose Items */}
                <div className="space-y-2">
                    {visibleRecents.length > 0 && (
                        <div className="text-[10px] font-black text-muted-foreground uppercase tracking-[0.2em] mb-4 mt-8 ml-1">Recent Commands</div>
                    )}

                    {visibleRecents.map((cmd, i) => (
                        <div
                            key={i}
                            className="group relative flex items-center p-3 rounded-2xl hover:bg-secondary transition-all duration-300 cursor-pointer border border-transparent hover:border-border"
                            onClick={() => onSelect(cmd)}
                        >
                            <span className="text-sm text-foreground truncate font-light flex-1 pr-8 tracking-wide">
                                {cmd}
                            </span>

                            {/* Actions Group */}
                            <div className="absolute right-3 opacity-0 group-hover:opacity-100 flex items-center gap-1 transition-all duration-300 translate-x-1 group-hover:translate-x-0">
                                <button
                                    onClick={(e) => handleDelete(cmd, e)}
                                    className="p-2 hover:bg-red-500 bg-[#0A0A12]/80 backdrop-blur-md rounded-xl text-slate-500 hover:text-white transition-all shadow-xl"
                                    title="Delete"
                                >
                                    <Trash2 className="w-3.5 h-3.5" />
                                </button>

                                {folders.length > 0 && (
                                    <div className="relative group/folder">
                                        <button className="p-2 hover:bg-primary bg-[#0A0A12]/80 backdrop-blur-md rounded-xl text-slate-500 hover:text-white transition-all shadow-xl">
                                            <Folder className="w-3.5 h-3.5" />
                                        </button>
                                        <div className="absolute right-0 bottom-full mb-2 w-40 glass-pane rounded-2xl shadow-2xl overflow-hidden hidden group-hover/folder:block z-50">
                                            <div className="p-2 bg-white/5 border-b border-white/5 text-[10px] font-bold text-slate-500 uppercase tracking-widest text-center">Move to</div>
                                            {folders.map(f => (
                                                <div
                                                    key={f.id}
                                                    onClick={(e) => addToFolder(cmd, f.id, e)}
                                                    className="px-4 py-2.5 text-xs text-slate-300 hover:bg-primary/20 hover:text-white cursor-pointer truncate transition-colors"
                                                >
                                                    {f.name}
                                                </div>
                                            ))}
                                        </div>
                                    </div>
                                )}
                            </div>
                        </div>
                    ))}
                </div>
            </div>
        </div>
    );
}

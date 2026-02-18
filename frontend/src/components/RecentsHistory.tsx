import { useState } from "react";
import { Clock, ChevronRight, Trash2, Folder, FolderPlus, MoreHorizontal } from "lucide-react";
import { cn } from "@/lib/utils";

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
        <div className="w-full h-full p-4 bg-[#0A0A12]">
            <div className="flex items-center justify-between mb-6">
                <div className="flex items-center gap-2 text-slate-400">
                    <Clock className="w-4 h-4" />
                    <h3 className="text-sm font-semibold uppercase tracking-wider">History</h3>
                </div>
                <button
                    onClick={() => setIsCreatingFolder(true)}
                    className="p-1 hover:bg-white/10 rounded-md text-slate-500 hover:text-slate-300 transition-colors"
                    title="New Folder"
                >
                    <FolderPlus className="w-4 h-4" />
                </button>
            </div>

            {/* Folder Creation Input */}
            {isCreatingFolder && (
                <div className="mb-4 p-2 bg-white/5 rounded-lg border border-white/10">
                    <input
                        type="text"
                        value={newFolderName}
                        onChange={(e) => setNewFolderName(e.target.value)}
                        placeholder="Folder name..."
                        className="w-full bg-transparent text-sm text-slate-200 outline-none placeholder:text-slate-600 mb-2"
                        autoFocus
                        onKeyDown={(e) => e.key === 'Enter' && handleCreateFolder()}
                    />
                    <div className="flex justify-end gap-2">
                        <button onClick={() => setIsCreatingFolder(false)} className="text-xs text-slate-500 hover:text-slate-300">Cancel</button>
                        <button onClick={handleCreateFolder} className="text-xs text-emerald-400 hover:text-emerald-300">Create</button>
                    </div>
                </div>
            )}

            <div className="space-y-4">
                {/* Folders List */}
                {folders.map(folder => (
                    <div key={folder.id} className="group">
                        <div className="flex items-center gap-2 text-slate-300 p-2 rounded-lg hover:bg-white/5 transition-colors cursor-pointer">
                            <Folder className="w-4 h-4 text-amber-500" />
                            <span className="text-sm font-medium flex-1">{folder.name}</span>
                            <span className="text-xs text-slate-600">{folder.items.length}</span>
                        </div>
                        {/* Expanded folder items could go here if we implemented toggle logic */}
                        {folder.items.length > 0 && (
                            <div className="pl-4 mt-1 space-y-1 border-l border-white/5 ml-2">
                                {folder.items.map((item, idx) => (
                                    <div key={idx} onClick={() => onSelect(item)} className="text-xs text-slate-400 py-1 px-2 hover:bg-white/5 rounded cursor-pointer truncate">
                                        {item}
                                    </div>
                                ))}
                            </div>
                        )}
                    </div>
                ))}

                {/* Loose Items */}
                <div className="space-y-1">
                    {visibleRecents.length > 0 && <div className="text-xs font-semibold text-slate-600 uppercase tracking-wider mb-2 mt-4 ml-1">Recent Items</div>}

                    {visibleRecents.map((cmd, i) => (
                        <div
                            key={i}
                            className="group relative flex items-center p-2 rounded-lg hover:bg-white/5 transition-colors cursor-pointer border border-transparent hover:border-white/5"
                            onClick={() => onSelect(cmd)}
                        >
                            <span className="text-sm text-slate-300 truncate font-light flex-1 pr-8">
                                {cmd}
                            </span>

                            {/* Actions Group */}
                            <div className="absolute right-2 opacity-0 group-hover:opacity-100 flex items-center gap-1 transition-opacity bg-[#0A0A12] pl-2 shadow-xl">
                                {/* Delete Button */}
                                <button
                                    onClick={(e) => handleDelete(cmd, e)}
                                    className="p-1.5 hover:bg-red-500/20 rounded text-slate-500 hover:text-red-400 transition-colors"
                                    title="Delete"
                                >
                                    <Trash2 className="w-3 h-3" />
                                </button>

                                {/* Move to Folder (Simple Dropdown equivalent) */}
                                {folders.length > 0 && (
                                    <div className="relative group/folder">
                                        <button className="p-1.5 hover:bg-blue-500/20 rounded text-slate-500 hover:text-blue-400 transition-colors">
                                            <Folder className="w-3 h-3" />
                                        </button>
                                        {/* Hover Menu for Folders */}
                                        <div className="absolute right-0 top-full mt-1 w-32 bg-slate-800 border border-slate-700 rounded-md shadow-xl overflow-hidden hidden group-hover/folder:block z-50">
                                            {folders.map(f => (
                                                <div
                                                    key={f.id}
                                                    onClick={(e) => addToFolder(cmd, f.id, e)}
                                                    className="px-3 py-2 text-xs text-slate-300 hover:bg-slate-700 cursor-pointer truncate"
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

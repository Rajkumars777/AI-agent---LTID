"""
src/services/desktop/file_index.py
====================================
Background filesystem indexer.
Walks all user folders and builds a fast in-memory + disk-persisted lookup cache.
Rebuilt automatically every REBUILD_INTERVAL seconds in a daemon thread.

Usage:
    from src.services.desktop.file_index import file_index
    results = file_index.search("budget.xlsx")   # → [full_path, ...]
    path    = file_index.find_one("chrome")       # → best match or None
"""

import os
import re
import json
import time
import threading
from pathlib import Path
from typing import Dict, List, Optional, Set


# ─────────────────────────────────────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────────────────────────────────────

USERPROFILE        = os.environ.get("USERPROFILE", os.path.expanduser("~"))
REBUILD_INTERVAL   = 600          # Rebuild full index every 10 minutes
CACHE_FILE         = os.path.join(USERPROFILE, ".ai_agent_file_index.json")
MAX_INDEX_SIZE     = 50_000       # Safety cap on number of indexed files

# All folders to scan (recursive)
SCAN_ROOTS: List[str] = [
    os.path.join(USERPROFILE, "Desktop"),
    os.path.join(USERPROFILE, "Documents"),
    os.path.join(USERPROFILE, "Downloads"),
    os.path.join(USERPROFILE, "Music"),
    os.path.join(USERPROFILE, "Pictures"),
    os.path.join(USERPROFILE, "Videos"),
    os.path.join(USERPROFILE, "OneDrive"),
    os.path.join(USERPROFILE, "AppData", "Roaming", "Microsoft", "Windows", "Start Menu"),
]

# Additional deep scan roots for executables / installed apps
APP_SCAN_ROOTS: List[str] = [
    os.environ.get("ProgramFiles",       "C:\\Program Files"),
    os.environ.get("ProgramFiles(x86)",  "C:\\Program Files (x86)"),
    os.environ.get("ProgramData",        "C:\\ProgramData"),
    os.path.join(USERPROFILE, "AppData", "Local"),
    os.path.join(USERPROFILE, "AppData", "Roaming"),
]

# File extensions that are "app launchers" — indexed from APP_SCAN_ROOTS
APP_EXTENSIONS: Set[str] = {".exe", ".lnk", ".url"}

# Skip these folder names entirely (too large / system-internal)
SKIP_DIRS: Set[str] = {
    "__pycache__", "node_modules", ".git", "site-packages",
    "WindowsApps", "WinSxS", "assembly", "GAC_64", "GAC_32",
    "installer", "temp", "tmp", "cache", "logs", "log",
}


# ─────────────────────────────────────────────────────────────────────────────
# INDEX
# ─────────────────────────────────────────────────────────────────────────────

class FileSystemIndex:
    """
    Thread-safe in-memory file index.
    
    Internal structure:
        _name_map:  {lowercase_basename → [full_path, ...]}   fast name lookup
        _path_set:  {full_path}                               dedup guard
    """

    def __init__(self):
        self._name_map:  Dict[str, List[str]] = {}
        self._path_set:  Set[str]             = set()
        self._lock       = threading.RLock()
        self._built      = False
        self._last_build = 0.0
        self._building   = False

        # Try loading from disk immediately for instant startup
        self._load_from_disk()

        # Start background builder
        self._start_background_build()

    # ── Public API ────────────────────────────────────────────────────────────

    def search(self, query: str, limit: int = 10, exact: bool = False) -> List[str]:
        """
        Search the index for files matching `query`.

        Args:
            query:  filename, partial name, or full path fragment
            limit:  max results to return
            exact:  if True only exact basename matches returned
        Returns:
            List of absolute paths, best matches first.
        """
        if not query:
            return []

        # If query looks like an absolute path, just check existence
        if os.path.isabs(query) and os.path.exists(query):
            return [query]

        query_lower = query.lower().strip()
        results: List[str] = []

        with self._lock:
            if exact:
                # Exact basename match
                for path in self._name_map.get(query_lower, []):
                    if os.path.exists(path):
                        results.append(path)
            else:
                # Substring match on basename
                for name, paths in self._name_map.items():
                    if query_lower in name:
                        for p in paths:
                            if os.path.exists(p):
                                results.append(p)
                        if len(results) >= limit * 3:
                            break

        # Sort: exact match first, then shorter paths (more likely to be top-level)
        results.sort(key=lambda p: (
            0 if os.path.basename(p).lower() == query_lower else 1,
            len(p)
        ))

        return results[:limit]

    def find_one(self, query: str, exact: bool = False) -> Optional[str]:
        """Return the single best matching path or None."""
        results = self.search(query, limit=1, exact=exact)
        return results[0] if results else None

    def add(self, path: str):
        """Add a newly created/moved file to the index without full rebuild."""
        path = os.path.abspath(path)
        name = os.path.basename(path).lower()
        with self._lock:
            if path not in self._path_set:
                self._path_set.add(path)
                self._name_map.setdefault(name, []).append(path)
        
        # Persist manual change immediately
        self._save_to_disk()

    def remove(self, path: str):
        """Remove a deleted/moved file from the index."""
        path = os.path.abspath(path)
        name = os.path.basename(path).lower()
        with self._lock:
            self._path_set.discard(path)
            if name in self._name_map:
                self._name_map[name] = [p for p in self._name_map[name] if p != path]
                if not self._name_map[name]:
                    del self._name_map[name]
        
        # Persist manual change immediately
        self._save_to_disk()

    @property
    def is_ready(self) -> bool:
        return self._built

    @property
    def size(self) -> int:
        with self._lock:
            return len(self._path_set)

    # ── Build logic ───────────────────────────────────────────────────────────

    def _start_background_build(self):
        """Kick off background index build in a daemon thread."""
        t = threading.Thread(target=self._build_loop, daemon=True, name="FileIndexer")
        t.start()

    def _build_loop(self):
        """Continuously rebuild the index every REBUILD_INTERVAL seconds."""
        # Initial rebuild if disk load didn't happen or not built
        if not self._built:
            self._rebuild()

        while True:
            if time.time() - self._last_build >= REBUILD_INTERVAL or not self._built:
                self._rebuild()
            time.sleep(30)  # Check every 30s whether a rebuild is due

    def _rebuild(self):
        """Walk all scan roots and rebuild the full index."""
        if self._building:
            return
        self._building = True
        print("[FileIndex] 🔍 Starting full filesystem scan...")
        start = time.time()

        new_map:  Dict[str, List[str]] = {}
        new_set:  Set[str]             = set()
        count = 0

        # ── User files (all extensions) ──
        for root in SCAN_ROOTS:
            if not os.path.isdir(root):
                continue
            for dirpath, dirnames, filenames in os.walk(root, topdown=True):
                # Prune skipped dirs in-place
                dirnames[:] = [
                    d for d in dirnames
                    if d.lower() not in SKIP_DIRS and not d.startswith(".")
                ]
                for fname in filenames:
                    if count >= MAX_INDEX_SIZE:
                        break
                    full = os.path.join(dirpath, fname)
                    key  = fname.lower()
                    new_map.setdefault(key, []).append(full)
                    new_set.add(full)
                    count += 1

        # ── App launchers (exe/lnk only from program roots) ──
        for root in APP_SCAN_ROOTS:
            if not os.path.isdir(root):
                continue
            for dirpath, dirnames, filenames in os.walk(root, topdown=True):
                dirnames[:] = [
                    d for d in dirnames
                    if d.lower() not in SKIP_DIRS
                ]
                for fname in filenames:
                    if count >= MAX_INDEX_SIZE:
                        break
                    ext = os.path.splitext(fname)[1].lower()
                    if ext not in APP_EXTENSIONS:
                        continue
                    full = os.path.join(dirpath, fname)
                    key  = fname.lower()
                    new_map.setdefault(key, []).append(full)
                    new_set.add(full)
                    count += 1

        # Swap in new index atomically
        with self._lock:
            self._name_map  = new_map
            self._path_set  = new_set

        self._built      = True
        self._last_build = time.time()
        self._building   = False
        elapsed = time.time() - start
        print(f"[FileIndex] ✅ Indexed {count:,} files in {elapsed:.1f}s")

        # Persist to disk for fast next startup
        self._save_to_disk()

    def _save_to_disk(self):
        """Persist name→paths map to JSON for fast next startup."""
        try:
            with open(CACHE_FILE, "w", encoding="utf-8") as f:
                json.dump({
                    "ts":       self._last_build,
                    "name_map": self._name_map
                }, f, separators=(",", ":"))
        except Exception as e:
            print(f"[FileIndex] Cache save error: {e}")

    def _load_from_disk(self):
        """Load persisted index from disk if fresh enough."""
        if not os.path.exists(CACHE_FILE):
            return
        try:
            with open(CACHE_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            age = time.time() - data.get("ts", 0)
            if age < REBUILD_INTERVAL:
                with self._lock:
                    self._name_map = data["name_map"]
                    self._path_set = {p for paths in data["name_map"].values() for p in paths}
                self._built      = True
                self._last_build = data["ts"]
                print(f"[FileIndex] ⚡ Loaded {len(self._path_set):,} files from disk cache (age: {age:.0f}s)")
        except Exception as e:
            print(f"[FileIndex] Cache load error: {e}")


# ─────────────────────────────────────────────────────────────────────────────
# SINGLETON
# ─────────────────────────────────────────────────────────────────────────────

file_index = FileSystemIndex()

"""
ui_cache.py
===========
Caches UI element positions per application to avoid repeated OCR scans.
First time: OCR finds element (2s), saves position
Next time: Direct click at cached position (0.1s)
"""

import os
import json
import time
from typing import Optional, Tuple, Dict
from pathlib import Path

CACHE_FILE = Path.home() / ".agent_cache" / "ui_positions.json"
CACHE_TTL  = 3600  # 1 hour — UI positions change if window resizes

class UICache:
    """
    Caches UI element positions per (app, element) pair.
    Dramatically speeds up repeated interactions.
    """
    
    def __init__(self):
        self.cache: Dict[str, Dict] = {}
        self._load_cache()
    
    def _load_cache(self):
        """Load cached positions from disk."""
        if CACHE_FILE.exists():
            try:
                with open(CACHE_FILE, "r") as f:
                    self.cache = json.load(f)
                print(f"[UICache] Loaded {len(self.cache)} cached apps")
            except Exception as e:
                print(f"[UICache] Load error: {e}")
                self.cache = {}
    
    def _save_cache(self):
        """Save cache to disk."""
        try:
            CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
            with open(CACHE_FILE, "w") as f:
                json.dump(self.cache, f, indent=2)
        except Exception as e:
            print(f"[UICache] Save error: {e}")
    
    def get(
        self,
        app_name: str,
        element_text: str
    ) -> Optional[Tuple[int, int]]:
        """
        Get cached coordinates for an element.
        Returns None if not cached or expired.
        """
        cache_key = f"{app_name.lower()}:{element_text.lower()}"
        
        if cache_key not in self.cache:
            return None
        
        entry     = self.cache[cache_key]
        timestamp = entry.get("timestamp", 0)
        
        # Check if expired
        if time.time() - timestamp > CACHE_TTL:
            print(f"[UICache] Expired: {cache_key}")
            del self.cache[cache_key]
            return None
        
        coords = entry.get("coords")
        if coords:
            print(f"[UICache] ✅ Hit: {cache_key} → {coords}")
            return tuple(coords)
        
        return None
    
    def set(
        self,
        app_name: str,
        element_text: str,
        coords: Tuple[int, int]
    ):
        """Cache element coordinates."""
        cache_key = f"{app_name.lower()}:{element_text.lower()}"
        
        self.cache[cache_key] = {
            "coords": list(coords),
            "timestamp": time.time()
        }
        
        print(f"[UICache] 💾 Cached: {cache_key} → {coords}")
        self._save_cache()
    
    def invalidate_app(self, app_name: str):
        """Clear all cached positions for an app (e.g. after window resize)."""
        app_lower = app_name.lower()
        keys_to_remove = [k for k in self.cache.keys() if k.startswith(f"{app_lower}:")]
        
        for key in keys_to_remove:
            del self.cache[key]
        
        if keys_to_remove:
            print(f"[UICache] 🗑️ Invalidated {len(keys_to_remove)} entries for '{app_name}'")
            self._save_cache()
    
    def clear(self):
        """Clear entire cache."""
        self.cache = {}
        self._save_cache()
        print("[UICache] 🗑️ Cleared all cache")


# Global instance
ui_cache = UICache()

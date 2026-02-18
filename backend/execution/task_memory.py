"""
Task Memory System
==================
Persistent memory for tracking state across browser interactions.
Enables cross-site comparisons, multi-step tasks, and conditional logic.
"""

from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from datetime import datetime
import json


@dataclass
class ExtractedData:
    """Single piece of extracted data with metadata"""
    key: str
    value: Any
    source_url: str
    timestamp: datetime = field(default_factory=datetime.now)
    data_type: str = "text"  # text, price, rating, number, etc.
    
    def to_dict(self) -> Dict:
        return {
            "key": self.key,
            "value": self.value,
            "source_url": self.source_url,
            "timestamp": self.timestamp.isoformat(),
            "data_type": self.data_type
        }


@dataclass
class TaskState:
    """Current state of a task execution"""
    task_id: str
    goal: str
    current_step: int = 0
    total_steps: int = 0
    status: str = "running"  # running, completed, failed, paused
    error: Optional[str] = None
    
    def to_dict(self) -> Dict:
        return {
            "task_id": self.task_id,
            "goal": self.goal,
            "current_step": self.current_step,
            "total_steps": self.total_steps,
            "status": self.status,
            "error": self.error
        }


class TaskMemory:
    """
    Manages persistent state and extracted data across browser interactions.
    Supports multi-step tasks, cross-site comparisons, and conditional logic.
    """
    
    def __init__(self, task_id: str = "default"):
        self.task_id = task_id
        self.extracted_data: Dict[str, ExtractedData] = {}
        self.visited_urls: List[str] = []
        self.current_url: Optional[str] = None
        self.state: Optional[TaskState] = None
        self.context: Dict[str, Any] = {}  # Free-form context storage
        self.execution_log: List[Dict] = []
        
    def store_extracted_data(self, key: str, value: Any, source_url: str, 
                            data_type: str = "text") -> None:
        """Store a piece of extracted data with metadata"""
        self.extracted_data[key] = ExtractedData(
            key=key,
            value=value,
            source_url=source_url,
            data_type=data_type
        )
        print(f"[Memory] Stored: {key} = {value} (from {source_url})")
        
    def get_extracted_data(self, key: str) -> Optional[Any]:
        """Retrieve extracted data by key"""
        data = self.extracted_data.get(key)
        return data.value if data else None
    
    def get_all_extracted_data(self) -> Dict[str, Any]:
        """Get all extracted data as key-value pairs"""
        return {k: v.value for k, v in self.extracted_data.items()}
    
    def get_data_by_source(self, source_url: str) -> Dict[str, Any]:
        """Get all data extracted from a specific URL"""
        return {
            k: v.value 
            for k, v in self.extracted_data.items() 
            if source_url in v.source_url
        }
    
    def add_visited_url(self, url: str) -> None:
        """Track a visited URL"""
        if url not in self.visited_urls:
            self.visited_urls.append(url)
        self.current_url = url
        
    def set_context(self, key: str, value: Any) -> None:
        """Store arbitrary context data"""
        self.context[key] = value
        
    def get_context(self, key: str, default: Any = None) -> Any:
        """Retrieve context data"""
        return self.context.get(key, default)
    
    def log_action(self, action: str, result: str, metadata: Dict = None) -> None:
        """Log an action for debugging and tracking"""
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "action": action,
            "result": result,
            "url": self.current_url,
            "metadata": metadata or {}
        }
        self.execution_log.append(log_entry)
        
    def update_state(self, **kwargs) -> None:
        """Update task state"""
        if not self.state:
            self.state = TaskState(task_id=self.task_id, goal=kwargs.get("goal", ""))
        
        for key, value in kwargs.items():
            if hasattr(self.state, key):
                setattr(self.state, key, value)
    
    def get_state(self) -> Optional[Dict]:
        """Get current task state"""
        return self.state.to_dict() if self.state else None
    
    def compare_data(self, key_pattern: str) -> Dict[str, Any]:
        """
        Compare extracted data across multiple sources.
        
        Example: compare_data("price") returns all price data from different sites
        """
        results = {}
        for key, data in self.extracted_data.items():
            if key_pattern.lower() in key.lower():
                site = self._extract_site_from_url(data.source_url)
                results[site] = {
                    "value": data.value,
                    "source": data.source_url,
                    "timestamp": data.timestamp.isoformat()
                }
        return results
    
    def _extract_site_from_url(self, url: str) -> str:
        """Extract site name from URL"""
        from urllib.parse import urlparse
        domain = urlparse(url).netloc
        # Clean up: www.amazon.in -> amazon
        site = domain.replace("www.", "").split(".")[0]
        return site.capitalize()
    
    def clear(self) -> None:
        """Clear all memory for fresh start"""
        self.extracted_data.clear()
        self.visited_urls.clear()
        self.current_url = None
        self.context.clear()
        self.execution_log.clear()
        self.state = None
        
    def to_dict(self) -> Dict:
        """Serialize memory to dict for storage/debugging"""
        return {
            "task_id": self.task_id,
            "extracted_data": {k: v.to_dict() for k, v in self.extracted_data.items()},
            "visited_urls": self.visited_urls,
            "current_url": self.current_url,
            "context": self.context,
            "state": self.state.to_dict() if self.state else None,
            "execution_log": self.execution_log[-20:]  # Last 20 entries
        }
    
    def __repr__(self) -> str:
        return f"TaskMemory(task_id={self.task_id}, extracted={len(self.extracted_data)}, urls={len(self.visited_urls)})"


# Global memory instance for the current task
_current_memory: Optional[TaskMemory] = None


def get_task_memory(task_id: str = "default", create: bool = True) -> Optional[TaskMemory]:
    """Get or create task memory instance"""
    global _current_memory
    
    if not _current_memory and create:
        _current_memory = TaskMemory(task_id)
    elif _current_memory and _current_memory.task_id != task_id and create:
        # New task, create fresh memory
        _current_memory = TaskMemory(task_id)
    
    return _current_memory


def clear_task_memory() -> None:
    """Clear global task memory"""
    global _current_memory
    if _current_memory:
        _current_memory.clear()
    _current_memory = None

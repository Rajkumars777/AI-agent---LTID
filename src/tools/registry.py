import os
import json
import importlib.util
import sys
from typing import Dict, Any, List, Optional, Callable

GENERATED_TOOLS_DIR = os.path.join(os.path.dirname(__file__), "generated")
REGISTRY_FILE = os.path.join(os.path.dirname(__file__), "registry.json")

class ToolsRegistry:
    def __init__(self):
        os.makedirs(GENERATED_TOOLS_DIR, exist_ok=True)  # Ensure folder exists
        self.tools: Dict[str, Dict[str, Any]] = {}       # name -> metadata/schema
        self.executors: Dict[str, Callable] = {}         # name -> function
        self._load_registry()

    def _load_registry(self):
        """Loads saved tool metadata and attempts to reload executors."""
        if os.path.exists(REGISTRY_FILE):
            try:
                with open(REGISTRY_FILE, "r") as f:
                    self.tools = json.load(f)
                
                for name in list(self.tools.keys()):
                    success = self._load_executor(name)
                    if not success:
                        filepath = os.path.join(GENERATED_TOOLS_DIR, f"{name}.py")
                        if not os.path.exists(filepath):
                            print(f"[Registry] Removing orphaned tool: {name}")
                            del self.tools[name]
                
                self._save_registry()
            except Exception as e:
                print(f"[Registry] Error loading registry file: {e}")

    def register(self, tool_def: Dict[str, Any], executor_fn: Optional[Callable] = None, is_core: bool = False):
        """Adds a tool to the registry. Only generated tools are saved to disk."""
        name = tool_def["name"]
        
        # Add a core flag to metadata
        tool_def["_is_core"] = is_core
        
        self.tools[name] = tool_def
        if executor_fn:
            self.executors[name] = executor_fn
            
        # Only persistent generated tools go to the JSON file
        if not is_core:
            self._save_registry()
            
        print(f"[Registry] Tool registered: {name} {'(Core)' if is_core else '(Generated)'}")

    def _save_registry(self):
        """Saves ONLY non-core tool metadata to disk."""
        try:
            # Filter matches only generated tools
            generated_tools = {k: v for k, v in self.tools.items() if not v.get("_is_core", False)}
            with open(REGISTRY_FILE, "w") as f:
                json.dump(generated_tools, f, indent=2)
        except Exception as e:
            print(f"[Registry] Error saving registry: {e}")

    def _load_executor(self, tool_name: str) -> bool:
        """Dynamically imports the 'execute' function from a generated tool file."""
        filepath = os.path.join(GENERATED_TOOLS_DIR, f"{tool_name}.py")
        if not os.path.exists(filepath):
            return False
        
        try:
            # Use unique namespaced module name to avoid collision
            spec = importlib.util.spec_from_file_location(f"generated_tools.{tool_name}", filepath)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            
            if hasattr(module, "execute"):
                self.executors[tool_name] = module.execute
                return True
        except Exception as e:
            print(f"[Registry] Failed to load executor for {tool_name}: {e}")
        return False

    def has_tool(self, name: str) -> bool:
        """Helper to check tool existence."""
        return name in self.tools

    def get_definitions(self) -> List[Dict[str, Any]]:
        """Returns all tool schemas for LLM tool-calling."""
        return list(self.tools.values())

    async def execute(self, name: str, params: Dict[str, Any]) -> str:
        """Routes execution to the correct function (supports async/sync)."""
        if name not in self.executors:
            # Attempt a late reload in case it was just generated
            if self._load_executor(name):
                print(f"[Registry] Late-loaded executor for {name}")
            else:
                return f"[Error] Tool '{name}' not found in registry."

        fn = self.executors[name]
        try:
            import asyncio
            if asyncio.iscoroutinefunction(fn):
                return await fn(params)
            else:
                return fn(params)
        except Exception as e:
            return f"[Error] Tool Execution Error ({name}): {str(e)}"

    def rollback(self, tool_name: str) -> bool:
        """Removes a tool and its source file if it fails dry-run."""
        existed = tool_name in self.tools
        if tool_name in self.tools:
            del self.tools[tool_name]
        if tool_name in self.executors:
            del self.executors[tool_name]
        
        filepath = os.path.join(GENERATED_TOOLS_DIR, f"{tool_name}.py")
        if os.path.exists(filepath):
            try:
                os.remove(filepath)
            except:
                pass
        self._save_registry()
        print(f"[Registry] Rolled back tool: {tool_name}")
        return existed

# Global instance
registry = ToolsRegistry()

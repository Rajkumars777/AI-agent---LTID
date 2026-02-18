"""
core_tools.py
=============
Bootstraps the tool registry with all built-in capabilities.
Each tool has a schema (for LLM tool calling) and an executor (Python function).
"""

from capabilities.desktop_ops        import (
    open_application, rename_file, move_file,
    delete_file, copy_file, list_files,
    resolve_target_path, _is_visual_rpa, _get_rpa_target
)
from capabilities.desktop_automation import desktop_agent
from typing import Any, Dict, List, Optional
from tools.registry                  import registry


# ─────────────────────────────────────────────────────
# EXECUTOR FUNCTIONS
# Routes core actions through handlers.py for rich results
# ─────────────────────────────────────────────────────

async def _exec_via_handler(action: str, params: dict) -> Any:
    """Helper to route tool calls through the rich handle_action logic."""
    from execution.handlers import handle_action
    
    # Extract target and context from params
    # Tools often use "target" or "query" or "directory" as the primary arg
    target  = params.get("target") or params.get("query") or params.get("directory") or params.get("url") or params.get("text")
    context = params.get("destination") or params.get("new_name") or params.get("window_title") or params.get("extension")
    
    # Call the rich handler
    res = await handle_action(
        action     = action,
        target     = str(target) if target else "",
        context    = str(context) if context else None,
        user_input = f"{action} {target} {context or ''}",
        task_id    = "agent_tool"
    )
    
    # Return the result part (agent.py handles the wrapping)
    # We might want to return the whole dict if agent.py is updated to handle it
    return res

async def _exec_open_app(p: dict) -> Any:
    return await _exec_via_handler("OPEN", p)

async def _exec_rename(p: dict) -> Any:
    return await _exec_via_handler("RENAME", p)

async def _exec_move(p: dict) -> Any:
    return await _exec_via_handler("MOVE", p)

async def _exec_copy(p: dict) -> Any:
    return await _exec_via_handler("COPY", p)

async def _exec_delete(p: dict) -> Any:
    return await _exec_via_handler("DELETE", p)

async def _exec_list(p: dict) -> Any:
    return await _exec_via_handler("LIST_FILES", p)

async def _exec_search(p: dict) -> Any:
    return await _exec_via_handler("SEARCH", p) # Handlers will need a SEARCH entry or fallback

async def _exec_read_screen(p: dict) -> Any:
    return await _exec_via_handler("READ_SCREEN", p)

async def _exec_screenshot(p: dict) -> Any:
    return await _exec_via_handler("SCREENSHOT", p)

async def _exec_click_text(p: dict) -> Any:
    return await _exec_via_handler("CLICK_TEXT", p)

async def _exec_type_on_screen(p: dict) -> Any:
    return await _exec_via_handler("TYPE_DESKTOP", p)

async def _exec_press_key(p: dict) -> Any:
    return await _exec_via_handler("PRESS_KEY", p) # Need to ensure handle_action has this

async def _exec_scroll(p: dict) -> Any:
    return await _exec_via_handler("SCROLL", p) # Need entry in handlers.py

async def _exec_browse_web(p: dict) -> Any:
    return await _exec_via_handler("WEB_CONTROL", p)

async def _exec_web_search(p: dict) -> Any:
    # Build a search URL query for handler
    import urllib.parse
    q = p.get("query", "")
    p["target"] = f"https://www.google.com/search?q={urllib.parse.quote(q)}"
    return await _exec_via_handler("WEB_CONTROL", p)

async def _exec_search_start_menu(p: dict) -> Any:
    return await _exec_via_handler("SEARCH_START_MENU", p)


# ─────────────────────────────────────────────────────
# CORE TOOL DEFINITIONS
# ─────────────────────────────────────────────────────

CORE_TOOLS = [

    # ── FILE SYSTEM ──────────────────────────────────

    {
        "name": "open_app",
        "description": (
            "Opens any application, file, or document. "
            "Essential for 'open [filename]', 'launch [app]', or 'start [program]' commands."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "target": {"type": "string", "description": "App name or file path to open"}
            },
            "required": ["target"]
        },
        "executor": _exec_open_app
    },

    {
        "name": "rename_item",
        "description": (
            "Renames a file or shortcut. "
            "Use when user says: rename, change name, call it, give it a new name."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "target":   {"type": "string", "description": "Current file name or path"},
                "new_name": {"type": "string", "description": "New name for the file"}
            },
            "required": ["target", "new_name"]
        },
        "executor": _exec_rename
    },

    {
        "name": "move_item",
        "description": (
            "Moves a file to a new folder. "
            "Use when user says: move, put in, transfer to, relocate, send to folder."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "target":      {"type": "string", "description": "File name or path to move"},
                "destination": {"type": "string", "description": "Destination folder (e.g. Music, Downloads, Desktop)"}
            },
            "required": ["target", "destination"]
        },
        "executor": _exec_move
    },

    {
        "name": "copy_item",
        "description": (
            "Copies a file to a new location. "
            "Use when user says: copy, duplicate, backup, make a copy of."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "target":      {"type": "string", "description": "File name or path to copy"},
                "destination": {"type": "string", "description": "Destination folder"}
            },
            "required": ["target", "destination"]
        },
        "executor": _exec_copy
    },

    {
        "name": "delete_item",
        "description": (
            "Deletes a single file. "
            "Use when user says: delete, remove, trash, get rid of."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "target": {"type": "string", "description": "File name or path to delete"}
            },
            "required": ["target"]
        },
        "executor": _exec_delete
    },

    {
        "name": "list_items",
        "description": (
            "Lists files in a folder. "
            "Use when user says: list, show files, what's in, show folder contents."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "directory": {"type": "string", "description": "Folder to list (e.g. Downloads, Desktop, Documents)"},
                "extension": {"type": "string", "description": "Optional filter by file type (e.g. .pdf, .xlsx)"}
            },
            "required": ["directory"]
        },
        "executor": _exec_list
    },

    {
        "name": "search_item",
        "description": (
            "Searches for a file or application. "
            "Use when user says: find, search, where is, locate, look for."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "File name, app name, or search term"}
            },
            "required": ["query"]
        },
        "executor": _exec_search
    },

    # ── VISUAL RPA ────────────────────────────────────

    {
        "name": "read_screen",
        "description": (
            "Reads all visible text on the screen via OCR. "
            "Use when user says: read screen, what do you see, read what's on screen."
        ),
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": []
        },
        "executor": _exec_read_screen
    },

    {
        "name": "take_screenshot",
        "description": (
            "Captures a screenshot of the screen. "
            "Use when user says: screenshot, capture screen, take a picture of screen."
        ),
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": []
        },
        "executor": _exec_screenshot
    },

    {
        "name": "click_text_on_screen",
        "description": (
            "Finds text on screen and clicks it. "
            "Use when user says: click, press, tap on text/button visible on screen."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "text":         {"type": "string",  "description": "Text to find and click on screen"},
                "double_click": {"type": "boolean", "description": "True for double-click, False for single"},
                "window_title": {"type": "string",  "description": "Optional: restrict search to this window"}
            },
            "required": ["text"]
        },
        "executor": _exec_click_text
    },

    {
        "name": "type_on_screen",
        "description": (
            "Types text physically on the keyboard. "
            "Use when user says: type [text], enter [text], write [text], input [number], or 'type this'."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "text":         {"type": "string", "description": "The exact string or number to type"},
                "window_title": {"type": "string", "description": "Optional: Window to focus before typing"}
            },
            "required": ["text"]
        },
        "executor": _exec_type_on_screen
    },

    {
        "name": "press_key",
        "description": (
            "Presses a keyboard key. "
            "Use when user says: press enter, press escape, hit tab, press delete."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "key": {"type": "string", "description": "Key name: enter, esc, tab, delete, space, up, down, left, right"}
            },
            "required": ["key"]
        },
        "executor": _exec_press_key
    },

    {
        "name": "scroll_screen",
        "description": (
            "Scrolls the mouse wheel up or down. "
            "Use when user says: scroll up, scroll down, scroll the page."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "clicks": {"type": "integer", "description": "Positive = scroll up, Negative = scroll down"},
                "x":      {"type": "integer", "description": "Optional X coordinate to scroll at"},
                "y":      {"type": "integer", "description": "Optional Y coordinate to scroll at"}
            },
            "required": ["clicks"]
        },
        "executor": _exec_scroll
    },

    {
        "name": "search_start_menu",
        "description": (
            "Searches Windows Start Menu visually to open an app. "
            "Use as fallback when open_app fails or for UWP/Store apps."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "query":  {"type": "string", "description": "App name to search in Start Menu"},
                "action": {"type": "string", "description": "open (default), click, or find"}
            },
            "required": ["query"]
        },
        "executor": _exec_search_start_menu
    },

    # ── BROWSER ───────────────────────────────────────

    {
        "name": "browse_web",
        "description": (
            "Opens a website or URL in the browser. "
            "Use when user says: go to, open website, browse, visit, navigate to."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "Full URL or domain (e.g. youtube.com, https://google.com)"}
            },
            "required": ["url"]
        },
        "executor": _exec_browse_web
    },

    {
        "name": "web_search",
        "description": (
            "Searches the web for information. "
            "Use when user says: search online, google, look up, find information about."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query"}
            },
            "required": ["query"]
        },
        "executor": _exec_web_search
    },

    # ── ORCHESTRATOR SIGNALS ──────────────────────────

    {
        "name": "MULTI_STEP_COMPLETE",
        "description": "Internal signal for completed multi-step tasks.",
        "input_schema": {"type": "object", "properties": {}, "required": []},
        "executor": lambda p: _exec_via_handler("MULTI_STEP_COMPLETE", p)
    },

    {
        "name": "MULTI_STEP_FAILED",
        "description": "Internal signal for failed multi-step tasks.",
        "input_schema": {"type": "object", "properties": {}, "required": []},
        "executor": lambda p: _exec_via_handler("MULTI_STEP_FAILED", p)
    },

]


# ─────────────────────────────────────────────────────
# BOOTSTRAP
# ─────────────────────────────────────────────────────

def initialize_core_tools():
    """
    Registers all core tools into the registry.
    Skips tools already registered to prevent double-registration on re-import.
    """
    registered = 0
    skipped    = 0

    for tool in CORE_TOOLS:
        if registry.has_tool(tool["name"]):
            skipped += 1
            continue

        # Separate schema from executor
        meta     = {k: v for k, v in tool.items() if k != "executor"}
        executor = tool["executor"]
        registry.register(meta, executor, is_core=True)
        registered += 1

    print(f"[CoreTools] ✅ Registered {registered} tools "
          f"({skipped} already existed, {len(CORE_TOOLS)} total)")


# Auto-initialize when imported as part of the backend package
if __name__ == "backend.tools.core_tools" or __name__ == "tools.core_tools":
    initialize_core_tools()

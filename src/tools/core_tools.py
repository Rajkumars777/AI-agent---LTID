"""
src/tools/core_tools.py
========================
Bootstraps the tool registry with all built-in capabilities.

Design rules:
  - ALL service imports are LAZY (inside executor functions).
  - No top-level imports from src.services.desktop.* to prevent circular
    import / startup crash if a dependency is missing.
  - Each tool has: name, description, input_schema, executor (async fn).
"""

from typing import Any
import urllib.parse

from src.tools.registry import registry


# ─────────────────────────────────────────────────────────────────────────────
# EXECUTOR HELPERS
# ─────────────────────────────────────────────────────────────────────────────

async def _via_handler(action: str, params: dict) -> Any:
    """Route any action through the central handle_action dispatcher."""
    from src.core.execution.handlers import handle_action

    target  = (params.get("target") or params.get("query") or
               params.get("directory") or params.get("url") or
               params.get("text") or params.get("key") or "")
    context = (params.get("destination") or params.get("new_name") or
               params.get("window_title") or params.get("extension") or
               params.get("action") or None)

    return await handle_action(
        action     = action,
        target     = str(target),
        context    = str(context) if context else None,
        user_input = f"{action} {target}",
        task_id    = "agent_tool",
    )


# ── Desktop / File ops ────────────────────────────────────────────────────────

async def _exec_open(p: dict) -> Any:
    return await _via_handler("OPEN", p)

async def _exec_close(p: dict) -> Any:
    return await _via_handler("CLOSE", p)

async def _exec_rename(p: dict) -> Any:
    return await _via_handler("RENAME", p)

async def _exec_move(p: dict) -> Any:
    return await _via_handler("MOVE", p)

async def _exec_copy(p: dict) -> Any:
    return await _via_handler("COPY", p)

async def _exec_delete(p: dict) -> Any:
    return await _via_handler("DELETE", p)

async def _exec_delete_folder(p: dict) -> Any:
    from src.services.desktop.ops import delete_folder
    return delete_folder(p.get("target"))

async def _exec_create_folder(p: dict) -> Any:
    from src.services.desktop.ops import create_folder
    return create_folder(p.get("folder_name"), p.get("location", "."))

async def _exec_create_file(p: dict) -> Any:
    from src.services.desktop.ops import create_file
    return create_file(p.get("file_name"), p.get("location", "."), p.get("content", ""))

async def _exec_get_info(p: dict) -> Any:
    from src.services.desktop.ops import get_item_info
    return get_item_info(p.get("target"))

async def _exec_list_files(p: dict) -> Any:
    return await _via_handler("LIST_FILES", p)

async def _exec_search(p: dict) -> Any:
    return await _via_handler("SEARCH", p)

# ── Visual RPA ────────────────────────────────────────────────────────────────

async def _exec_screenshot(p: dict) -> Any:
    return await _via_handler("SCREENSHOT", p)

async def _exec_read_screen(p: dict) -> Any:
    return await _via_handler("READ_SCREEN", p)

async def _exec_click_text(p: dict) -> Any:
    return await _via_handler("CLICK_TEXT", p)

async def _exec_type_on_screen(p: dict) -> Any:
    return await _via_handler("TYPE_DESKTOP", p)

async def _exec_press_key(p: dict) -> Any:
    return await _via_handler("PRESS_KEY", p)

async def _exec_scroll(p: dict) -> Any:
    return await _via_handler("SCROLL", p)

async def _exec_start_menu(p: dict) -> Any:
    return await _via_handler("SEARCH_START_MENU", p)

# ── Browser ───────────────────────────────────────────────────────────────────

async def _exec_browse(p: dict) -> Any:
    return await _via_handler("WEB_CONTROL", p)

async def _exec_web_search(p: dict) -> Any:
    q = p.get("query", "")
    p["url"] = f"https://www.google.com/search?q={urllib.parse.quote(q)}"
    return await _via_handler("WEB_CONTROL", p)

async def _exec_analyze_screen(p: dict) -> Any:
    return await _via_handler("ANALYZE_SCREEN_AND_ACT", p)

# ── Messenger ────────────────────────────────────────────────────────────────

async def _exec_whatsapp(p: dict) -> Any:
    from src.services.desktop.screen_agent import run_screen_task
    task_desc = f'whatsapp send "{p.get("message", "")}" to {p.get("contact", "")}'
    return await run_screen_task(task_desc)

async def _exec_email(p: dict) -> Any:
    from src.services.desktop.screen_agent import run_screen_task
    task_desc = f'send mail to {p.get("recipient", "")} subject: {p.get("subject", "No Subject")} body: {p.get("body", "")}'
    return await run_screen_task(task_desc)

# ── Excel ────────────────────────────────────────────────────────────────────

async def _exec_excel_read(p: dict) -> Any:
    return await _via_handler("EXCEL_READ", p)

async def _exec_excel_write(p: dict) -> Any:
    # "context" in handle_action takes: sheet, cell, val (comma sep)
    val = f'{p.get("sheet_name", "")}, {p.get("cell", "")}, {p.get("value", "")}'
    p["context"] = val
    return await _via_handler("EXCEL_WRITE", p)

async def _exec_excel_add_row(p: dict) -> Any:
    p["context"] = p.get("data", "")
    return await _via_handler("EXCEL_ADD_ROW", p)

async def _exec_excel_delete_row(p: dict) -> Any:
    p["context"] = str(p.get("row_index", ""))
    return await _via_handler("EXCEL_DELETE_ROW", p)

async def _exec_excel_style(p: dict) -> Any:
    p["context"] = f'{p.get("cell_range", "")}, {p.get("style", "")}'
    return await _via_handler("EXCEL_STYLE", p)

async def _exec_excel_refresh_pivots(p: dict) -> Any:
    return await _via_handler("EXCEL_REFRESH_PIVOTS", p)



# ─────────────────────────────────────────────────────────────────────────────
# TOOL DEFINITIONS
# ─────────────────────────────────────────────────────────────────────────────

CORE_TOOLS = [

    # ── Excel Operations ──────────────────────────────────────────────────────

    {
        "name": "read_excel_sheet",
        "description": "Reads data from an Excel sheet. Returns an HTML or markdown preview of the rows.",
        "input_schema": {
            "type": "object",
            "properties": {
                "target": {"type": "string", "description": "Excel file path or name"},
                "sheet_name": {"type": "string", "description": "Optional sheet name to read"}
            },
            "required": ["target"]
        },
        "executor": _exec_excel_read,
    },
    {
        "name": "write_excel_cell",
        "description": "Writes a specific value to an Excel cell (e.g. A1, B2).",
        "input_schema": {
            "type": "object",
            "properties": {
                "target": {"type": "string", "description": "Excel file path or name"},
                "sheet_name": {"type": "string", "description": "Optional sheet name"},
                "cell": {"type": "string", "description": "Target cell (e.g. 'A1', 'B2')"},
                "value": {"type": "string", "description": "Value to write into the cell"}
            },
            "required": ["target", "cell", "value"]
        },
        "executor": _exec_excel_write,
    },
    {
        "name": "append_excel_row",
        "description": "Appends a new row of data to the end of an Excel sheet.",
        "input_schema": {
            "type": "object",
            "properties": {
                "target": {"type": "string", "description": "Excel file path or name"},
                "data": {"type": "string", "description": "Comma-separated values or key=value pairs for the row data"}
            },
            "required": ["target", "data"]
        },
        "executor": _exec_excel_add_row,
    },
    {
        "name": "delete_excel_row",
        "description": "Deletes a specific row in an Excel file by its index (e.g., 5, or 'last').",
        "input_schema": {
            "type": "object",
            "properties": {
                "target": {"type": "string", "description": "Excel file path or name"},
                "row_index": {"type": "string", "description": "Row index to delete (e.g. '5' or 'last')"}
            },
            "required": ["target", "row_index"]
        },
        "executor": _exec_excel_delete_row,
    },
    {
        "name": "style_excel_cells",
        "description": "Applies a background/font color or styling to an Excel cell or row/column (e.g., 'A1:D1', 'headers').",
        "input_schema": {
            "type": "object",
            "properties": {
                "target": {"type": "string", "description": "Excel file path or name"},
                "cell_range": {"type": "string", "description": "Range to style, e.g. 'A1', 'headers', 'row 1'"},
                "style": {"type": "string", "description": "Color name or style (e.g. 'green', 'bold', 'border')"}
            },
            "required": ["target", "cell_range", "style"]
        },
        "executor": _exec_excel_style,
    },
    {
        "name": "refresh_excel_pivots",
        "description": "Configures all pivot tables in the Excel file to refresh on next load.",
        "input_schema": {
            "type": "object",
            "properties": {
                "target": {"type": "string", "description": "Excel file path or name"}
            },
            "required": ["target"]
        },
        "executor": _exec_excel_refresh_pivots,
    },

    # ── File & App Operations ─────────────────────────────────────────────────

    {
        "name": "open_item",
        "description": (
            "Opens any application or file on the system by name, path, or alias. "
            "Works for installed apps (Chrome, Word, Spotify, etc.), files (budget.xlsx), "
            "and folders. If the file/app isn't found by path, falls back to Start Menu search. "
            "Use when user says: open, launch, run, start, show."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "target": {
                    "type": "string",
                    "description": "App name (e.g. 'chrome'), file name (e.g. 'budget.xlsx'), or full path"
                }
            },
            "required": ["target"]
        },
        "executor": _exec_open,
    },

    {
        "name": "close_item",
        "description": (
            "Closes a running application by name or window title. "
            "Use when user says: close, quit, exit, kill, stop."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "target": {
                    "type": "string",
                    "description": "App name or window title to close (e.g. 'chrome', 'notepad', 'Spotify')"
                }
            },
            "required": ["target"]
        },
        "executor": _exec_close,
    },

    {
        "name": "rename_file",
        "description": (
            "Renames a file. Extension is preserved automatically if not given. "
            "Use when user says: rename, change name of."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "target":   {"type": "string", "description": "File name or path to rename"},
                "new_name": {"type": "string", "description": "New name (with or without extension)"}
            },
            "required": ["target", "new_name"]
        },
        "executor": _exec_rename,
    },

    {
        "name": "move_file",
        "description": (
            "Moves a file to a destination folder. "
            "Destination can be an alias like 'music', 'desktop', 'downloads', or a full path. "
            "Use when user says: move, transfer, send to."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "target":      {"type": "string", "description": "File name or path"},
                "destination": {"type": "string", "description": "Destination folder or alias"}
            },
            "required": ["target", "destination"]
        },
        "executor": _exec_move,
    },

    {
        "name": "copy_file",
        "description": (
            "Copies a file to a destination folder. "
            "Use when user says: copy, duplicate, backup to."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "target":      {"type": "string", "description": "File name or path"},
                "destination": {"type": "string", "description": "Destination folder or alias"}
            },
            "required": ["target", "destination"]
        },
        "executor": _exec_copy,
    },

    {
        "name": "delete_file",
        "description": (
            "Deletes a single file (folders are blocked for safety). "
            "Use when user says: delete, remove, trash."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "target": {"type": "string", "description": "File name or path to delete"}
            },
            "required": ["target"]
        },
        "executor": _exec_delete,
    },

    {
        "name": "delete_folder",
        "description": "Deletes a folder and all its contents. CAUTION: Action is irreversible.",
        "input_schema": {
            "type": "object",
            "properties": {
                "target": {"type": "string", "description": "Folder name or path"}
            },
            "required": ["target"]
        },
        "executor": _exec_delete_folder,
    },

    {
        "name": "create_folder",
        "description": "Creates a new folder at the specified location.",
        "input_schema": {
            "type": "object",
            "properties": {
                "folder_name": {"type": "string", "description": "Name of the new folder"},
                "location":    {"type": "string", "description": "Location alias (desktop, documents, etc.) or path"}
            },
            "required": ["folder_name"]
        },
        "executor": _exec_create_folder,
    },

    {
        "name": "create_file",
        "description": "Creates a new text file with optional content.",
        "input_schema": {
            "type": "object",
            "properties": {
                "file_name": {"type": "string", "description": "Name of the file (e.g. notes.txt)"},
                "location":  {"type": "string", "description": "Location alias or path"},
                "content":   {"type": "string", "description": "Optional text content"}
            },
            "required": ["file_name"]
        },
        "executor": _exec_create_file,
    },

    {
        "name": "get_file_info",
        "description": "Gets detailed metadata about a file or folder.",
        "input_schema": {
            "type": "object",
            "properties": {
                "target": {"type": "string", "description": "File/folder name or path"}
            },
            "required": ["target"]
        },
        "executor": _exec_get_info,
    },

    {
        "name": "list_files",
        "description": (
            "Lists files in a folder. Supports aliases: desktop, documents, downloads, music, pictures, videos. "
            "Use when user says: list, show files in, what's in."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "directory": {"type": "string", "description": "Folder path or alias (e.g. 'downloads', 'desktop')"},
                "extension": {"type": "string", "description": "Optional filter e.g. '.pdf', '.mp3'"}
            },
            "required": ["directory"]
        },
        "executor": _exec_list_files,
    },

    {
        "name": "find_file",
        "description": (
            "Searches the system for a file or folder by name. "
            "Use when user says: find, search for, where is, locate."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "File or folder name to search for"}
            },
            "required": ["query"]
        },
        "executor": _exec_search,
    },

    # ── Visual RPA ────────────────────────────────────────────────────────────

    {
        "name": "take_screenshot",
        "description": "Captures a screenshot of the current screen.",
        "input_schema": {"type": "object", "properties": {}, "required": []},
        "executor": _exec_screenshot,
    },

    {
        "name": "read_screen",
        "description": "Reads all visible text on screen via OCR.",
        "input_schema": {"type": "object", "properties": {}, "required": []},
        "executor": _exec_read_screen,
    },

    {
        "name": "analyze_and_act_on_screen",
        "description": "Analyzes the current visible screen using AI and autonomously performs the sequence of actions necessary to complete the given task.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "A natural language task description to complete on screen"}
            },
            "required": ["query"]
        },
        "executor": _exec_analyze_screen,
    },

    {
        "name": "click_text_on_screen",
        "description": (
            "Finds text visible on screen and clicks it. "
            "Use when user says: click, press, tap on something visible."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "text":         {"type": "string",  "description": "Text to find and click"},
                "double_click": {"type": "boolean", "description": "True for double-click"},
                "window_title": {"type": "string",  "description": "Optional: restrict to this window"}
            },
            "required": ["text"]
        },
        "executor": _exec_click_text,
    },

    {
        "name": "type_on_screen",
        "description": "Types text on the keyboard into the focused window.",
        "input_schema": {
            "type": "object",
            "properties": {
                "text":         {"type": "string", "description": "Text to type"},
                "window_title": {"type": "string", "description": "Optional: window to focus first"}
            },
            "required": ["text"]
        },
        "executor": _exec_type_on_screen,
    },

    {
        "name": "press_key",
        "description": "Presses a keyboard key (enter, esc, tab, delete, etc.).",
        "input_schema": {
            "type": "object",
            "properties": {
                "key": {"type": "string", "description": "Key name: enter, esc, tab, delete, space, up, down"}
            },
            "required": ["key"]
        },
        "executor": _exec_press_key,
    },

    {
        "name": "scroll_screen",
        "description": "Scrolls the mouse wheel up or down.",
        "input_schema": {
            "type": "object",
            "properties": {
                "clicks": {"type": "integer", "description": "Positive = up, Negative = down"},
                "x":      {"type": "integer", "description": "Optional X coordinate"},
                "y":      {"type": "integer", "description": "Optional Y coordinate"}
            },
            "required": ["clicks"]
        },
        "executor": _exec_scroll,
    },

    {
        "name": "search_start_menu",
        "description": (
            "Searches Windows Start Menu to open any app. "
            "Use as explicit fallback when open_item doesn't work."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "query":  {"type": "string", "description": "App name to search"},
                "action": {"type": "string", "description": "open (default) or find"}
            },
            "required": ["query"]
        },
        "executor": _exec_start_menu,
    },

    # ── Browser ───────────────────────────────────────────────────────────────

    {
        "name": "browse_web",
        "description": "Opens a website or URL in the browser.",
        "input_schema": {
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "Full URL or domain (e.g. youtube.com)"}
            },
            "required": ["url"]
        },
        "executor": _exec_browse,
    },

    {
        "name": "web_search",
        "description": "Searches the web via Google.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query"}
            },
            "required": ["query"]
        },
        "executor": _exec_web_search,
    },

    # ── Messenger ─────────────────────────────────────────────────────────────

    {
        "name": "send_whatsapp_message",
        "description": "Sends a WhatsApp message to a contact.",
        "input_schema": {
            "type": "object",
            "properties": {
                "contact": {"type": "string", "description": "Contact name as it appears in WhatsApp"},
                "message": {"type": "string", "description": "Message to send"}
            },
            "required": ["contact", "message"]
        },
        "executor": _exec_whatsapp,
    },

    {
        "name": "send_email",
        "description": "Sends an email.",
        "input_schema": {
            "type": "object",
            "properties": {
                "recipient": {"type": "string", "description": "Recipient email address"},
                "subject":   {"type": "string", "description": "Subject line"},
                "body":      {"type": "string", "description": "Email body"}
            },
            "required": ["recipient", "body"]
        },
        "executor": _exec_email,
    },
]


# ─────────────────────────────────────────────────────────────────────────────
# BOOTSTRAP
# ─────────────────────────────────────────────────────────────────────────────

def initialize_core_tools():
    """Register all core tools. Always overwrites to ensure core precedence."""
    registered = 0
    for tool in CORE_TOOLS:
        meta     = {k: v for k, v in tool.items() if k != "executor"}
        executor = tool["executor"]
        registry.register(meta, executor, is_core=True)
        registered += 1
    print(f"[CoreTools] [OK] {registered} core tools initialized (precedence ensured)")


# Auto-initialize when imported as part of the package
if __name__ in ("src.tools.core_tools", "tools.core_tools", "__main__"):
    initialize_core_tools()

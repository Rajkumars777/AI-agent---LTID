"""
nlu.py
======
Natural Language Understanding using Native Tool Calling.
Converts user queries into structured Commands using the tool registry.
Triggers Self-Evolution (generator.py) when no tool matches.
"""

import os
import json
import asyncio
import concurrent.futures
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

from src.tools.registry import registry
from src.tools.generator import generator

# ─────────────────────────────────────────────────────
# CONSTANTS
# ─────────────────────────────────────────────────────

EVOLUTION_TIMEOUT  = 30.0   # max seconds to wait for tool generation
LLM_MODEL          = "llama-3.3-70b-versatile"
FALLBACK_MODEL     = "llama-3.1-8b-instant"
MAX_HISTORY_MSGS   = 10     # max past messages to include for context

# ─────────────────────────────────────────────────────
# MODELS
# ─────────────────────────────────────────────────────

from pydantic import BaseModel, Field

class Command(BaseModel):
    action:    str
    params:    Dict[str, Any] = Field(default_factory=dict)
    reasoning: Optional[str] = ""


# ─────────────────────────────────────────────────────
# NLU ENGINE
# ─────────────────────────────────────────────────────

class NLUEngine:
    """
    Converts natural language to structured Commands.
    Uses native tool calling — no JSON string parsing.
    Auto-evolves new tools when no match found.
    """

    def __init__(self):
        self._client = None
        self._model = LLM_MODEL

    @property
    def client(self):
        if self._client:
            return self._client
            
        groq_key = os.getenv("GROQ_API_KEY")
        if groq_key:
            self._client = Groq(api_key=groq_key)
            self._model = LLM_MODEL
            print("[NLU] Using Groq API")
            return self._client
            
        or_key = os.getenv("OPENROUTER_API_KEY")
        if or_key:
            from openai import OpenAI
            self._client = OpenAI(
                base_url="https://openrouter.ai/api/v1",
                api_key=or_key
            )
            # Use a good general purpose model for OpenRouter
            self._model = "google/gemini-2.0-flash-001" 
            print(f"[NLU] Using OpenRouter API (Model: {self._model})")
            return self._client
            
        raise ValueError("No API Key found. Set GROQ_API_KEY or OPENROUTER_API_KEY.")

    # ─────────────────────────────────────
    # PUBLIC: Main entry point
    # ─────────────────────────────────────

    async def get_commands(
        self,
        text:          str,
        chat_history:  List[Dict[str, str]] = None,
        evolved_skill: str = None
    ) -> List[Command]:
        """
        Main entry point. Converts any user query into Commands.
        """
        print(f"\n[NLU] Analyzing: '{text}'")

        # ── Step -1: Categorize Query ──
        category = "DESKTOP_AUTOMATION" # default
        lower_text = text.lower()
        
        # Data retrieval keywords — highest priority (stock data, market data + Excel creation)
        data_retrieval_keywords = [
            "stock", "closing", "opening", "price", "retrieve", "fetch",
            "nikkei", "sensex", "nifty", "s&p", "dow", "nasdaq",
            "exchange rate", "currency rate", "gold price", "silver price",
            "crypto", "bitcoin", "market data", "share price",
            "stock average", "closing value", "opening value",
        ]
        
        web_keywords = [
            "http", "https", "www", ".com", ".org", ".net", ".io", ".dev",
            "browser", "chrome", "edge", "brave", "firefox",
            "website", "webpage", "web page", "gmail", "youtube", "google",
            "search web", "search the web", "web search",
            "go to ", "navigate to", "visit ", "browse to",
            "wikipedia", "amazon", "facebook", "twitter", "reddit",
        ]
        file_keywords = [".xlsx", ".xls", ".csv", ".txt", ".pdf", ".docx", "file", "folder", "directory", "rename", "move", "copy", "delete file", "excel", "word", "notepad", "open file", "close file", "c:\\\\", "d:\\\\", "c:/", "d:/", "downloads", "desktop", "documents", "drive"]
        
        # Check data retrieval FIRST (stock + Excel = data task, not simple file manipulation)
        import re
        is_data_task = any(kw in lower_text for kw in data_retrieval_keywords)
        has_file_target = bool(re.search(r'\b\w+\.(xlsx|xls|csv)\b', lower_text))
        
        if is_data_task:
            category = "DATA_RETRIEVAL"
        # Check for explicit URLs (highest priority for web)
        elif bool(re.search(r'\b\w+\.(com|org|net|io|dev|edu|gov|co)\b', lower_text)) or any(kw in lower_text for kw in web_keywords):
            category = "WEB_AUTOMATION"
        # Then check files so local paths stay as FILE_MANIPULATION
        elif any(kw in lower_text for kw in file_keywords) or "\\" in lower_text:
            category = "FILE_MANIPULATION"
            
        print(f"[NLU] 🎯 Query Category: {category}")

        # ── Step 0: Detect multi-step tasks ──
        is_multi_step = self._is_multi_step_task(text)
        
        # Fast path for DATA_RETRIEVAL: route directly to DYNAMIC_CODE handler
        if category == "DATA_RETRIEVAL":
            # Extract target filename from query (e.g., "stock.xlsx")
            file_match = re.search(r'\b(\w+\.(xlsx|xls|csv))\b', lower_text)
            target_file = file_match.group(1) if file_match else "stock_data.xlsx"
            
            # Resolve Downloads path if mentioned
            import os
            user_home = os.path.expanduser("~")
            if "download" in lower_text:
                target_file = os.path.join(user_home, "Downloads", target_file)
            elif "desktop" in lower_text:
                target_file = os.path.join(user_home, "Desktop", target_file)
            elif "document" in lower_text:
                target_file = os.path.join(user_home, "Documents", target_file)
            else:
                target_file = os.path.join(user_home, "Downloads", target_file)
            
            print(f"[NLU] 📊 Data retrieval task → DYNAMIC_CODE, target: {target_file}")
            return [Command(
                action    = "DYNAMIC_CODE",
                params    = {"target": target_file},
                reasoning = f"Data retrieval task routed to code generator. File: {target_file}"
            )]

        # Fast path directly to IntelligentWebAutomation
        if category == "WEB_AUTOMATION":
            print("[NLU] 🌐 Handling via direct web automation wrapper")
            return [Command(
                action    = "WEB_CONTROL",
                params    = {"target": text},
                reasoning = "Natively handling via IntelligentWebAutomation parser"
            )]

        if is_multi_step and not evolved_skill:
             print("[NLU] 🔗 Multi-step task detected — routing to planner + executor")
             from src.core.execution.multistep_planner import plan_multistep
             from src.core.execution.multistep_executor import execute_multistep_plan

             plan = await asyncio.to_thread(plan_multistep, text)

             if plan and len(plan.steps) > 0:
                 print(f"[NLU] Plan: intent='{plan.intent}', {len(plan.steps)} steps")

                 # Execute the plan — we need an emit_event function.
                 # Create a no-op if we don't have one here (the executor will
                 # still work, just without live frontend events).
                 async def _noop_emit(tid, ev, data):
                     pass

                 results = await execute_multistep_plan(
                     plan       = plan,
                     task_id    = "nlu_multistep",
                     emit_event = _noop_emit,
                 )

                 succeeded = sum(1 for r in results if r.get("success"))
                 total     = len(results)

                 if succeeded > 0:
                     summary_parts = [r.get("content", "") for r in results]
                     return [Command(
                         action    = "MULTI_STEP_COMPLETE",
                         params    = {"summary": "\n".join(summary_parts), "steps": str(total)},
                         reasoning = f"Executed {succeeded}/{total} steps successfully"
                     )]
                 else:
                     return [Command(
                         action    = "MULTI_STEP_FAILED",
                         params    = {"error": "All steps failed"},
                         reasoning = "Multi-step execution failed"
                     )]
             else:
                 print("[NLU] Planner returned no plan — falling through to standard NLU")

        # ... standard NLU flow ...
        
        chat_history = chat_history or []

        # Step 1: Build Groq-format tool list from registry
        from src.tools.core_tools import initialize_core_tools
        initialize_core_tools()
        groq_tools = self._build_tool_schemas(registry)

        # Step 2: Build messages
        messages = self._build_messages(text, chat_history, evolved_skill)

        # Step 3: Call LLM with tool calling
        try:
            # Attempt with Primary Model
            try:
                response = await asyncio.to_thread(
                    self.client.chat.completions.create,
                    model       = self._model,
                    messages    = messages,
                    tools       = groq_tools if groq_tools else None,
                    tool_choice = "auto" if groq_tools else None,
                    temperature = 0.1
                )
            except Exception as e:
                if "rate_limit" in str(e).lower() or "429" in str(e):
                    print(f"[NLU] ⚠️ Rate limit on 70b. Falling back to {FALLBACK_MODEL}...")
                    response = await asyncio.to_thread(
                        self.client.chat.completions.create,
                        model       = FALLBACK_MODEL,
                        messages    = messages,
                        tools       = groq_tools if groq_tools else None,
                        tool_choice = "auto" if groq_tools else None,
                        temperature = 0.1
                    )
                else:
                    raise e

            message = response.choices[0].message

            # ── Scenario A: Tool selected ──
            if hasattr(message, "tool_calls") and message.tool_calls:
                commands = self._parse_tool_calls(message.tool_calls)
                if commands:
                    print(f"[NLU] ✅ Tool selected: {commands[0].action}")
                    return commands

            # ── Scenario B: No tool matched → EVOLVE (only once) ──
            if not evolved_skill:
                print(f"[NLU] No tool matched. Triggering evolution...")
                new_tool = await self._evolve_with_timeout(generator, text)

                if new_tool:
                    print(f"[NLU] 🎉 Evolved: '{new_tool['name']}'. Retrying...")
                    return await self.get_commands(
                        text          = text,
                        chat_history  = chat_history,
                        evolved_skill = new_tool["name"]
                    )

            # ── Scenario C: Text response ──
            if message.content and message.content.strip():
                return [Command(
                    action    = "ANSWER",
                    params    = {"text": message.content.strip()},
                    reasoning = "Direct LLM response."
                )]

        except Exception as e:
            print(f"[NLU] Error: {e}")
            return await self._fallback_without_tools(messages, e)

        # Nothing worked
        print("[NLU] ⚠️ No command could be extracted")
        return []

    # ─────────────────────────────────────
    # PRIVATE: Builders
    # ─────────────────────────────────────

    def _build_tool_schemas(self, registry) -> List[Dict]:
        """Converts registry tool definitions to Groq/OpenRouter API format."""
        llm_tools = []
        for tool in registry.get_definitions():
            # Clean copy of the schema to avoid sending internal keys like _is_core to LLM
            schema = tool.get("input_schema", {"type": "object", "properties": {}}).copy()
            
            # Groq is picky: Ensure it's a valid JSON Schema object
            if "type" not in schema:
                schema["type"] = "object"
            if "properties" not in schema:
                schema["properties"] = {}
                
            # Groq will 400 if required arrays mention fields that don't exist
            if "required" in schema:
                valid_required = [req for req in schema["required"] if req in schema["properties"]]
                if valid_required:
                    schema["required"] = valid_required
                else:
                    del schema["required"]

            llm_tools.append({
                "type": "function",
                "function": {
                    "name":        tool["name"],
                    "description": tool["description"],
                    "parameters":  schema
                }
            })
        print(f"[NLU] {len(llm_tools)} tools available (sanitized)")
        return llm_tools

    def _build_messages(
        self,
        text:          str,
        chat_history:  List[Dict[str, str]],
        evolved_skill: str = None
    ) -> List[Dict]:
        """
        Builds the full messages array for the LLM.
        Passes chat history as proper message objects (not injected into system prompt).
        """
        evolution_hint = (
            f"\nNOTE: A new skill '{evolved_skill}' was just created. USE IT for this task."
            if evolved_skill else ""
        )

        system_prompt = f"""You are a powerful Windows Desktop AI Agent.
Your job is to fulfill user requests by selecting the correct tool.
{evolution_hint}

RULES:
1. If a tool exists for the task → use it immediately.
2. If NO tool matches → return a text response explaining what you can't do yet.
3. If the user mentions a filename (e.g. 'data.xlsx'), prefer opening it or acting on it.
4. Use conversation history to understand context (e.g. "move IT" = last mentioned file).
5. Extract parameters precisely from the user's message.
6. If the user says "type", "enter", or "write", use the 'type_on_screen' tool.
7. For compound commands (e.g. "Open Calculator and type 123"), RETURN MULTIPLE TOOLS.
   - First call 'open_item' with target "Calculator"
   - Second call 'type_on_screen' with text "123"
   - Do NOT collapse them into one answer.

8. For messaging (e.g. "WhatsApp 'hi' to Mom"), return a sequence of tools:
   - Call 'open_item' with target "WhatsApp"
   - Call 'type_on_screen' with text "Mom"
   - Call 'press_key' with key "enter"
   - Call 'type_on_screen' with text "hi"
   - Call 'press_key' with key "enter"

9. DO NOT use XML tags like <function>. Use standard tool calling.
"""

        messages = [{"role": "system", "content": system_prompt}]

        # ── ONE-SHOT EXAMPLE (Forces correct tool format) ──
        messages.append({"role": "user", "content": "Open Notepad"})
        messages.append({
            "role": "assistant",
            "tool_calls": [{
                "id": "call_example_1",
                "type": "function",
                "function": {
                    "name": "open_item",
                    "arguments": "{\"target\": \"Notepad\"}"
                }
            }]
        })
        messages.append({
            "role": "tool",
            "tool_call_id": "call_example_1",
            "name": "open_item",
            "content": "[Success] Opened Notepad"
        })

        # Add recent chat history as proper message objects
        # Limit to last MAX_HISTORY_MSGS to avoid token overflow
        recent_history = chat_history[-MAX_HISTORY_MSGS:]
        messages.extend(recent_history)

        # Add current user message
        messages.append({"role": "user", "content": text})

        return messages

    def _parse_tool_calls(self, tool_calls) -> List[Command]:
        """Parses LLM tool calls into Command objects."""
        commands = []
        for call in tool_calls:
            try:
                # Handle cases where arguments might be already a dict or a JSON string
                if isinstance(call.function.arguments, str):
                    args = json.loads(call.function.arguments)
                else:
                    args = call.function.arguments or {}
                
                commands.append(Command(
                    action    = call.function.name,
                    params    = args,
                    reasoning = f"Tool '{call.function.name}' selected."
                ))
            except Exception as e:
                print(f"[NLU] ⚠️ Error parsing tool call args for '{call.function.name}': {e}")
                continue
        return commands

    # ─────────────────────────────────────
    # PRIVATE: Evolution
    # ─────────────────────────────────────

    async def _evolve_with_timeout(self, generator, text: str) -> dict | None:
        """Runs tool evolution with a timeout to prevent hanging."""
        try:
            return await asyncio.wait_for(
                generator.generate_tool(text),
                timeout=EVOLUTION_TIMEOUT
            )
        except asyncio.TimeoutError:
            print(f"[NLU] ⏱️ Evolution timed out after {EVOLUTION_TIMEOUT}s")
            return None
        except Exception as e:
            print(f"[NLU] Evolution error: {e}")
            return None

    # ─────────────────────────────────────
    # PRIVATE: Fallback
    # ─────────────────────────────────────

    async def _fallback_without_tools(
        self,
        messages: List[Dict],
        original_error: Exception
    ) -> List[Command]:
        """
        Last resort fallback — retry WITHOUT tools.
        Used when a 400/schema error occurs with tools attached.
        """
        error_str = str(original_error)

        # Only retry on tool-related errors
        if not any(code in error_str for code in ["400", "invalid_tool", "schema"]):
            return []

        print("[NLU] 🔄 Retrying without tools (schema error fallback)...")
        try:
            res = await asyncio.to_thread(
                self.client.chat.completions.create,
                model                 = LLM_MODEL,
                messages              = messages,
                tools                 = None,     # no tools this time
                temperature           = 0.1,
                max_tokens            = 512,
            )
            content = res.choices[0].message.content
            if content and content.strip():
                print(f"[NLU] Fallback content: {content[:50]}...")
                cmd = Command(
                    action    = "ANSWER",
                    params    = {"text": content.strip()},
                    reasoning = "Safe fallback — tools removed due to schema error."
                )
                return [cmd]
        except Exception as e:
            print(f"[NLU] Fallback also failed: {e}")

        return []


    def _is_multi_step_task(self, query: str) -> bool:
        """
        Detects if a query requires multiple sequential actions.
        Indicators: "and", "then", multiple verbs.
        """
        query_low = query.lower()
        
        # Explicit keywords
        multi_step_keywords = [
            " and then ", " then ", " after that ",
            " and also ", " and send ", " and type ",
            " and search ", " and click ", " and open "
        ]
        
        if any(kw in query_low for kw in multi_step_keywords):
            return True
        
        # Multiple verbs check
        action_verbs = [
            "open", "close", "send", "type", "click",
            "search", "find", "move", "copy", "delete",
            "rename", "go to", "navigate", "browse"
        ]
        
        verb_count = sum(1 for verb in action_verbs if verb in query_low)
        return verb_count >= 2


# ─────────────────────────────────────────────────────
# GLOBAL INSTANCE
# ─────────────────────────────────────────────────────

_nlu_engine = NLUEngine()


# ─────────────────────────────────────────────────────
# PUBLIC FUNCTIONS
# ─────────────────────────────────────────────────────

async def get_commands_dynamic(
    text:         str,
    chat_history: List[Dict[str, str]] = None,
    evolved_skill: str = None
) -> List[Command]:
    """
    Async entry point.
    Use this from FastAPI, async agent loops, etc.
    """
    return await _nlu_engine.get_commands(
        text          = text,
        chat_history  = chat_history or [],
        evolved_skill = evolved_skill
    )


def get_commands(
    text:         str,
    chat_history: List[Dict[str, str]] = None
) -> List[Command]:
    """
    Sync bridge for legacy agent.py or non-async callers.
    Safely handles both running and non-running event loops.
    """
    import asyncio
    try:
        # Check if an event loop is already running (e.g. FastAPI, Jupyter)
        loop = asyncio.get_running_loop()

        # Running inside async context — use thread pool to avoid blocking
        print("[NLU] Running in existing event loop — using thread pool")
        with concurrent.futures.ThreadPoolExecutor() as pool:
            future = pool.submit(
                asyncio.run,
                get_commands_dynamic(text, chat_history or [])
            )
            return future.result(timeout=60)

    except RuntimeError:
        # No running event loop — safe to use asyncio.run directly
        return asyncio.run(get_commands_dynamic(text, chat_history or []))

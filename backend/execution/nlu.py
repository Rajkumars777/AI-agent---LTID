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

from tools.registry import registry
from tools.generator import generator

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
        self.client = Groq(api_key=os.getenv("GROQ_API_KEY"))

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

        # ── Step 0: Detect multi-step tasks ──
        is_multi_step = self._is_multi_step_task(text)

        if is_multi_step and not evolved_skill:
             print("[NLU] 🔗 Multi-step task detected — routing to orchestrator")
             from execution.task_orchestrator import orchestrator
             
             result = await orchestrator.execute_multi_step(text)
             
             if result["success"]:
                 return [Command(
                     action    = "MULTI_STEP_COMPLETE",
                     params    = {"summary": result["summary"], "steps": result["steps"]},
                     reasoning = f"Executed {result['steps']} steps successfully"
                 )]
             else:
                 # If orchestrator failed, maybe fall back to standard NLU?
                 # or just report failure.
                 print(f"[NLU] Orchestrator failed: {result.get('error')}")
                 return [Command(
                     action    = "MULTI_STEP_FAILED",
                     params    = {"error": result.get("error", "Unknown error")},
                     reasoning = "Multi-step execution failed"
                 )]

        # ... standard NLU flow ...
        
        chat_history = chat_history or []

        # Step 1: Build Groq-format tool list from registry

        # Step 1: Build Groq-format tool list from registry
        groq_tools = self._build_tool_schemas(registry)

        # Step 2: Build messages
        messages = self._build_messages(text, chat_history, evolved_skill)

        # Step 3: Call LLM with tool calling
        try:
            # Attempt with Primary Model (70b)
            try:
                response = await asyncio.to_thread(
                    self.client.chat.completions.create,
                    model       = LLM_MODEL,
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
   - First tool: open_app
   - Second tool: type_on_screen
   - Do NOT collapse them into one answer.

8. For messaging (e.g. "WhatsApp 'hi' to Mom"):
   - open_app("WhatsApp")
   - type_on_screen("Mom")
   - press_key("enter")
   - type_on_screen("hi")
   - press_key("enter")
"""

        messages = [{"role": "system", "content": system_prompt}]

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
                max_completion_tokens = 512,
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

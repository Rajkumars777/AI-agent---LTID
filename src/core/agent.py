"""
src/core/agent.py
==================
Main agent — routes any task to the correct handler.

Route 1: ANY desktop/screen task → ScreenAgent (autonomous visual control)
Route 2: Multi-step non-visual   → multistep_executor
Route 3: Single action           → NLU → registry (existing flow)

The ScreenAgent handles everything automatically:
  email, whatsapp, amazon orders, google search, any app.
  Self-healer handles popups, auth, OTP, captcha, loading, focus.
  When user input needed (login, OTP) → ask_user sends message to frontend.
"""

import dspy
from langgraph.graph import StateGraph, END
from typing import TypedDict, Annotated, List, Dict
import operator, os, re
from datetime import datetime
from dotenv import load_dotenv
from collections import deque
import asyncio

load_dotenv()


class AgentState(TypedDict):
    input:              str
    task_id:            str
    messages:           Annotated[List[str], operator.add]
    intermediate_steps: List[str]
    chat_history:       List[Dict[str, str]]


openrouter_key = os.getenv("OPENROUTER_API_KEY")
if openrouter_key:
    from src.core.llm.openrouter_adapter import OpenRouterAdapter
    lm = OpenRouterAdapter(model='google/gemini-2.0-flash-001', api_key=openrouter_key)
    dspy.settings.configure(lm=lm)


class MemoryManager:
    def __init__(self, max_turns=5):
        self.history = deque(maxlen=max_turns * 2)
    def add(self, u, a):
        self.history.append({"role":"user","content":str(u)})
        self.history.append({"role":"assistant","content":str(a)})
    def get(self): return list(self.history)


agent_memory = MemoryManager()


# ─────────────────────────────────────────────────────────────────────────────
# SCREEN TASK DETECTION
# Catches any task that involves controlling the desktop/apps
# ─────────────────────────────────────────────────────────────────────────────

SCREEN_PATTERNS = [
    r'send\s+.+?(email|mail|message|msg)\s+to\b',
    r'open\s+\w+\s+and\b',
    r'(gmail|outlook|mail)\b',
    r'whatsapp\b',
    r'(order|buy|purchase|add to cart)\b',
    r'(amazon|flipkart|meesho|myntra)\b',
    r'(youtube|spotify|netflix)\b',
    r'(type|click|fill|search)\s+.+?\s+in\s+\w+',
    r'(log\s*in|sign\s*in)\s+to\b',
    r'open\s+(chrome|firefox|edge|notepad|word|excel)',
    r'(google|bing|search)\s+for\b',
    r'play\s+.+?\s+on\b',
    r'(whatsapp|telegram|discord)\s+message\b',
]

def _is_screen_task(query: str) -> bool:
    q = query.lower()
    return any(re.search(p, q) for p in SCREEN_PATTERNS)


# ─────────────────────────────────────────────────────────────────────────────
# MAIN NODE
# ─────────────────────────────────────────────────────────────────────────────

async def execute_tool(state: AgentState):
    user_input   = state.get("input","")
    task_id      = state.get("task_id","default")
    chat_history = state.get("chat_history",[])
    steps        = []

    from src.api.routers.events import emit_event
    await emit_event(task_id, "Thinking", {"message": f"Analyzing: {user_input}"})

    from src.api.routers.events import emit_event
    await emit_event(task_id, "Thinking", {"message": f"Analyzing: {user_input}"})

    # ── UNIFIED BRAIN ────────────────────────────────────────────────────────
    from src.core.execution.orchestrator import orchestrator
    
    try:
        # The orchestrator now decides whether it's a visual task (ScreenAgent)
        # or a deterministic multi-step task (Planner/Executor)
        # It also handles single actions by falling back to ScreenAgent's loops.
        result_pkg = await orchestrator.execute(user_input, task_id, emit_event)
        
        # Format for StateGraph
        msg = result_pkg.get("summary", "Task completed")
        intermediate_steps = result_pkg.get("intermediate_steps", [])
        
        # If no internal steps from deterministic planner, add the final result
        if not intermediate_steps:
            intermediate_steps = [{
                "type":      "Action",
                "content":   msg,
                "timestamp": datetime.now().strftime("%I:%M:%S %p"),
                "tool":      "AI Agent",
                "success":   result_pkg.get("success", True),
            }]
            
        agent_memory.add(user_input, msg[:200])
        return {"messages": [msg], "intermediate_steps": intermediate_steps}

    except Exception as e:
        import traceback
        error_msg = f"❌ Agent Error: {e}"
        print(error_msg, traceback.format_exc())
        return {"messages": [error_msg], "intermediate_steps": []}


workflow = StateGraph(AgentState)
workflow.add_node("agent", execute_tool)
workflow.set_entry_point("agent")
workflow.add_edge("agent", END)
app = workflow.compile()


async def run_agent(user_input: str, task_id: str = "default"):
    import pygetwindow as gw
    try:
        win = gw.getActiveWindow()
        ctx = f'Active Window: "{win.title if win else "Unknown"}"'
    except: ctx = ""

    history = agent_memory.get()
    merged  = history + [{"role":"system","content":ctx}]
    result  = await app.ainvoke({
        "input": user_input, "task_id": task_id,
        "messages": [], "chat_history": merged,
        "intermediate_steps": [],
    })
    return {"steps": result.get("intermediate_steps", [])}

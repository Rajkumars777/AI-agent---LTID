import dspy
from langgraph.graph import StateGraph, END
from typing import TypedDict, Annotated, List, Dict
import operator
import os
from datetime import datetime
from dotenv import load_dotenv
from collections import deque
import pyperclip

load_dotenv()

# 2. Define State
class AgentState(TypedDict):
    input: str
    task_id: str
    messages: Annotated[List[str], operator.add]
    intermediate_steps: List[str]
    chat_history: List[Dict[str, str]] # Changed from str to list of dicts

# Configure DSPy
openrouter_key = os.getenv("OPENROUTER_API_KEY")

if openrouter_key:
    from llm.openrouter_adapter import OpenRouterAdapter
    print("Using OpenRouter Adapter...")
    lm = OpenRouterAdapter(
        model='google/gemini-2.0-flash-001',
        api_key=openrouter_key
    )
    dspy.settings.configure(lm=lm)
else:
    print("WARNING: No API Key found for DSPy. NLU will fail.")

class MemoryManager:
    def __init__(self, max_turns=5):
        self.history = deque(maxlen=max_turns * 2)

    def add_interaction(self, user_cmd, agent_response):
        self.history.append({"role": "user", "content": str(user_cmd)})
        self.history.append({"role": "assistant", "content": str(agent_response)})

    def get_messages(self) -> List[Dict[str, str]]:
        return list(self.history)

agent_memory = MemoryManager()

def get_system_context():
    # Clipboard content disabled as it confuses the NLU with previous conversation snapshots
    clipboard_content = "None"
    
    import pygetwindow as gw
    active_window = "Unknown"
    try:
        win = gw.getActiveWindow()
        if win: active_window = win.title
    except: pass
    
    return f"\n[System State]\nActive Window: \"{active_window}\""

async def execute_tool(state: AgentState):
    user_input = state.get('input', '')
    task_id = state.get('task_id', 'default')
    steps = []
    
    from routers.events import emit_event
    await emit_event(task_id, "Thinking", {"message": f"Analyzing: {user_input}"})

    # 1. Native Tool-Calling & Evolution
    from execution.nlu import get_commands_dynamic
    from tools.registry import registry
    from tools.generator import generator
    generator.registry = registry # Fix circular import dependency
    import tools.core_tools # Ensures core tools are registered
    
    chat_history = state.get('chat_history', []) # Default to empty list
    try:
        commands = await get_commands_dynamic(user_input, chat_history=chat_history)
        await emit_event(task_id, "NLU_Success", {"commands": [c.dict() for c in commands]})
    except Exception as e:
        print(f"AGENT ERROR: {e}")
        commands = []
        await emit_event(task_id, "Error", {"message": f"NLU/Evolution Error: {str(e)}"})

    if not commands:
         return {"messages": ["I couldn't fulfill that request."], "intermediate_steps": steps}

    final_results = []
    
    # 2. Dynamic Execution Loop via Registry
    for cmd in commands:
        action = cmd.action
        params = cmd.params
        
        # Scenario A: Standard Tool Execution
        if action != "ANSWER":
            await emit_event(task_id, "ActionStarted", {"action": action, "target": str(params)})
            
            # Execute via Registry (Supports hot-reloaded tools!)
            raw_result = await registry.execute(action, params)
            
            # Normalize result (Handle rich dicts vs plain strings)
            display_result = ""
            attachment = None
            
            if isinstance(raw_result, dict):
                display_result = raw_result.get("result", str(raw_result))
                attachment = raw_result.get("attachment")
            else:
                display_result = str(raw_result)
            
            await emit_event(task_id, "ActionResult", {"action": action, "result": display_result})
            final_results.append(display_result)
            
            steps.append({
                "type": "Action",
                "content": display_result,
                "timestamp": datetime.now().strftime("%I:%M:%S %p"),
                "attachment": attachment
            })
        
        # Scenario B: Direct Answer
        else:
            ans = params.get("text", "I'm not sure how to respond.")
            final_results.append(ans)
            steps.append({
                "type": "Reasoning",
                "content": ans,
                "timestamp": datetime.now().strftime("%I:%M:%S %p")
            })
    
    return {"messages": final_results, "intermediate_steps": steps}

# 4. Define Graph
workflow = StateGraph(AgentState)
workflow.add_node("agent", execute_tool)
workflow.set_entry_point("agent")
workflow.add_edge("agent", END)

app = workflow.compile()

async def run_agent(user_input: str, task_id: str = "default"):
    history = agent_memory.get_messages()
    system_ctx = get_system_context()
    
    # Merge history with current system context for NLU
    merged_history = history + [{"role": "system", "content": system_ctx}]
    
    inputs = {"input": user_input, "task_id": task_id, "messages": [], "chat_history": merged_history}
    result = await app.ainvoke(inputs)
    
    # Update memory with first result message
    res_msgs = result.get("messages", [])
    agent_msg = res_msgs[0] if res_msgs else "Success"
    agent_memory.add_interaction(user_input, str(agent_msg)[:200])
    
    return {"steps": result.get("intermediate_steps", [])}

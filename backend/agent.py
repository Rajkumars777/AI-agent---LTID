import dspy
from langgraph.graph import StateGraph, END
from typing import TypedDict, Annotated, List
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
    chat_history: str

# Configure DSPy
openrouter_key = os.getenv("OPENROUTER_API_KEY")

if openrouter_key:
    from execution.openrouter_adapter import OpenRouterAdapter
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
        self.history.append(f"User: {user_cmd}")
        self.history.append(f"Agent: {agent_response}")

    def get_context_string(self):
        if not self.history:
            return "No previous context."
        return "\n".join(self.history)

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

    # 1. Unified Command Extraction (Fast Path + LLM)
    from execution.nlu import get_commands
    chat_history = state.get('chat_history', '')
    try:
        commands = get_commands(user_input, chat_history=chat_history)
        await emit_event(task_id, "NLU_Success", {"commands": [c.dict() for c in commands]})
    except Exception as e:
        commands = []
        steps.append({
             "type": "Reasoning",
             "content": f"NLU Error: {str(e)}",
             "timestamp": datetime.now().strftime("%I:%M:%S %p")
        })
        await emit_event(task_id, "Error", {"message": f"NLU Error: {str(e)}"})

    # If NLU fails or returns empty
    if not commands:
         steps.append({
            "type": "Reasoning",
            "content": f"No commands extracted from '{user_input}'",
            "timestamp": datetime.now().strftime("%I:%M:%S %p")
        })
         return {"messages": ["I didn't understand that command."], "intermediate_steps": steps}

    final_results = []
    
    # Optimizer: Merge OPEN + GENERATE_ASYNC
    optimized_commands = []
    skip_next = False
    
    for i in range(len(commands)):
        if skip_next:
            skip_next = False
            continue
            
        cmd = commands[i]
        
        if cmd.action in ["OPEN", "LAUNCH"] and i + 1 < len(commands):
            next_cmd = commands[i+1]
            if next_cmd.action in ["TYPE", "WRITE"] and next_cmd.context == "GENERATE_ASYNC":
                next_cmd.context = f"GENERATE_ASYNC:{cmd.target}"
                continue
        
        optimized_commands.append(cmd)
        
    commands = optimized_commands

    # 2. Execution Loop
    from execution.handlers import handle_action
    from utils.resolver import resolve_file_arg
    
    for cmd in commands:
        action = cmd.action.upper()
        target = cmd.target
        context = cmd.context
        
        # SMART RESOLUTION: If target or context looks like a file, resolve to absolute path
        if target and "." in target and not target.startswith("http") and not os.path.isabs(target):
             target = resolve_file_arg(target)
        if context and "." in context and not context.startswith("http") and not os.path.isabs(context) and "/" not in context and "\\" not in context:
             # Only resolve context if it looks like a filename, not a sentence
             if len(context.split()) == 1:
                 context = resolve_file_arg(context)

        await emit_event(task_id, "ActionStarted", {"action": action, "target": target})

        # Execute Action via Handler
        exec_res = await handle_action(action, target, context, user_input, task_id=task_id, reasoning=cmd.reasoning)
        
        result = exec_res["result"]
        trace_logs = exec_res["trace_logs"]
        attachment = exec_res["attachment"]
        
        await emit_event(task_id, "ActionResult", {"action": action, "result": result, "logs": trace_logs})

        final_results.append(result)

        # Create Step Content
        block_content = f"**Task:** {action} {target}"
        if context:
            block_content += f" (in {context})"
            
        if trace_logs:
            block_content += "\n" + "\n".join([f"- {Log}" for Log in trace_logs])
            
        block_content += f"\n**Result:** {result}"
        
        step_data = {
            "type": "Action",
            "content": block_content,
            "timestamp": datetime.now().strftime("%I:%M:%S %p")
        }
        
        if attachment:
            step_data["attachment"] = attachment
            
        steps.append(step_data)
    
    return {"messages": final_results, "intermediate_steps": steps}

# 4. Define Graph
workflow = StateGraph(AgentState)
workflow.add_node("agent", execute_tool)
workflow.set_entry_point("agent")
workflow.add_edge("agent", END)

app = workflow.compile()

async def run_agent(user_input: str, task_id: str = "default"):
    current_context = agent_memory.get_context_string()
    system_ctx = get_system_context()
    full_history = current_context + system_ctx
    
    inputs = {"input": user_input, "task_id": task_id, "messages": [], "chat_history": full_history}
    result = await app.ainvoke(inputs)
    
    # Update memory with first result message
    res_msgs = result.get("messages", [])
    agent_msg = res_msgs[0] if res_msgs else "Success"
    agent_memory.add_interaction(user_input, str(agent_msg)[:200])
    
    return {"steps": result.get("intermediate_steps", [])}

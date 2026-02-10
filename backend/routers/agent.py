from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from agent import run_agent
import asyncio
from typing import Optional
import uuid

router = APIRouter(prefix="/agent", tags=["agent"])

# Track active tasks for cancellation
active_tasks: dict[str, asyncio.Task] = {}
cancelled_tasks: set[str] = set()

class AgentRequest(BaseModel):
    input: str
    task_id: Optional[str] = None

class CancelRequest(BaseModel):
    task_id: str

@router.post("/chat")
async def chat_with_agent(request: AgentRequest):
    """Run the AI Agent with the given input. Returns execution steps."""
    task_id = request.task_id or str(uuid.uuid4())
    
    # Check if already cancelled before starting
    if task_id in cancelled_tasks:
        cancelled_tasks.discard(task_id)
        return {"cancelled": True, "task_id": task_id, "steps": []}
    
    try:
        response = await run_agent(request.input)
        
        # Check if cancelled during execution
        if task_id in cancelled_tasks:
            cancelled_tasks.discard(task_id)
            return {"cancelled": True, "task_id": task_id, "steps": []}
        
        response["task_id"] = task_id
        return response
    except asyncio.CancelledError:
        return {"cancelled": True, "task_id": task_id, "steps": []}
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/cancel")
async def cancel_operation(request: CancelRequest):
    """Cancel an ongoing operation."""
    task_id = request.task_id
    cancelled_tasks.add(task_id)
    
    # Try to cancel the active task if it exists
    if task_id in active_tasks:
        task = active_tasks[task_id]
        task.cancel()
        del active_tasks[task_id]
        return {"success": True, "message": f"Task {task_id} cancelled"}
    
    return {"success": True, "message": f"Task {task_id} marked for cancellation"}

@router.get("/status")
async def get_status():
    """Get agent status."""
    return {
        "active_tasks": len(active_tasks),
        "cancelled_tasks": len(cancelled_tasks)
    }

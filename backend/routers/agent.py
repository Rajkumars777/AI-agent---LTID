from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from agent import run_agent
import asyncio
from typing import Optional, Any
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
        # ✅ Track task for cancellation
        task = asyncio.create_task(run_agent(request.input, task_id=task_id))
        active_tasks[task_id] = task
        
        response = await task
        
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
    finally:
        # Clean up active task
        if task_id in active_tasks:
            del active_tasks[task_id]

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

class ResumeRequest(BaseModel):
    task_id: str
    data: Any

@router.post("/resume")
async def resume_task(request: ResumeRequest):
    """Provide input to a task currently waiting in PauseState."""
    from execution.interaction import provide_user_input
    success = provide_user_input(request.task_id, request.data)
    if success:
        return {"success": True, "message": "Input received. Task resuming."}
    else:
        return {"success": False, "message": f"Task {request.task_id} not currently waiting for input."}

@router.get("/status")
async def get_status():
    """Get agent status."""
    return {
        "active_tasks": len(active_tasks),
        "cancelled_tasks": len(cancelled_tasks)
    }

import asyncio
from typing import Dict, Any, Optional

# Shared registry for active interaction requests
# Maps task_id -> asyncio.Event
_pending_responses: Dict[str, asyncio.Event] = {}
_response_data: Dict[str, Any] = {}

async def ask_user(task_id: str, question: str, data: Optional[Dict] = None) -> Any:
    """
    Pauses execution and waits for a response from the user via WebSocket/API.
    """
    from routers.events import emit_event
    
    event = asyncio.Event()
    _pending_responses[task_id] = event
    
    print(f"HIFL: Pausing task {task_id} for user help: {question}")
    await emit_event(task_id, "REQUIRE_HELP", {
        "question": question,
        "context": data
    })
    
    try:
        # Wait for the client to provide input
        # Timeout after 5 minutes to prevent infinite hangs
        await asyncio.wait_for(event.wait(), timeout=300.0)
        
        response = _response_data.get(task_id)
        print(f"HIFL: Received response for task {task_id}: {response}")
        return response
    
    except asyncio.TimeoutError:
        print(f"HIFL: Task {task_id} timed out waiting for user.")
        return {"error": "timeout", "message": "User did not respond in time."}
    
    finally:
        # Cleanup
        _pending_responses.pop(task_id, None)
        _response_data.pop(task_id, None)

def provide_user_input(task_id: str, data: Any):
    """
    Called by an API endpoint or WebSocket handler when the user provides the requested help.
    """
    if task_id in _pending_responses:
        _response_data[task_id] = data
        _pending_responses[task_id].set()
        return True
    return False

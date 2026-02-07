from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from agent import run_agent

router = APIRouter(prefix="/agent", tags=["agent"])

class AgentRequest(BaseModel):
    input: str

@router.post("/chat")
async def chat_with_agent(request: AgentRequest):
    """Run the AI Agent with the given input. Returns execution steps."""
    try:
        response = await run_agent(request.input)
        return response
    except Exception as e:
        import traceback
        traceback.print_exc() # Print to console
        raise HTTPException(status_code=500, detail=str(e))

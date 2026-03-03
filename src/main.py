import sys
import os
import asyncio
import logging
from dotenv import load_dotenv

# Load environment variables first
load_dotenv()

# Configure path (add root to sys.path so 'src' can be imported)

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Set event loop policy for Windows
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

from fastapi import FastAPI
from contextlib import asynccontextmanager
import uvicorn
from fastapi.middleware.cors import CORSMiddleware

# Import Routers (Corrected paths)
from src.api.routers import agent as agent_router
from src.api.routers import tools as tools_router
from src.api.routers import events as events_router
from src.api.routers import voice as voice_router

# Import Tools for Registration
from src.tools.core_tools import initialize_core_tools
from src.tools.document_intelligence_tools import register_document_tools

# Import Confirmation Handler
from src.core.execution.confirmation_handler import confirmation_manager
from src.tools.registry import registry
from pydantic import BaseModel

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup logic
    logger.info("Startup: Connecting to services...")
    
    initialize_core_tools()
    register_document_tools()
    
    logger.info("✅ Services ready")
    yield
    # Shutdown logic
    logger.info("Shutdown: Closing connections...")

app = FastAPI(lifespan=lifespan, title="AI Agent Backend")

# Allow CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(agent_router.router)
app.include_router(tools_router.router)
app.include_router(events_router.router)
app.include_router(voice_router.router, prefix="/api/voice", tags=["voice"])

# ── Confirmation Endpoints ──

class ConfirmationRequest(BaseModel):
    confirmation_id: str
    approved: bool

@app.post("/agent/confirm")
async def confirm_action(req: ConfirmationRequest):
    """User approves or denies a confirmation."""
    if req.approved:
        action_params = confirmation_manager.approve_confirmation(req.confirmation_id)
        if not action_params:
            return {"success": False, "error": "Confirmation not found or expired"}
        
        # Re-execute the action with confirmed=True
        # Get tool name from params (default to delete_item for backward compatibility)
        tool_name = action_params.pop("tool_name", "delete_item")
        
        try:
            result = await registry.execute(tool_name, action_params)
            return {"success": True, "result": result}
        except Exception as e:
            return {"success": False, "error": str(e)}
    else:
        confirmation_manager.deny_confirmation(req.confirmation_id)
        return {"success": True, "result": "❌ Action cancelled by user"}

@app.get("/agent/pending_confirmations")
async def get_pending_confirmations(user_id: str):
    """Returns list of pending confirmations for a user."""
    confirmations = [
        {
            "id": cid,
            "message": conf["message"],
            "type": conf["type"]
        }
        for cid, conf in confirmation_manager.pending_confirmations.items()
        if conf["user_id"] == user_id
    ]
    return {"confirmations": confirmations}

@app.get("/")
async def read_root():
    return {"status": "online", "service": "AI Agent Backend"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

def main():
    uvicorn.run(
        "src.main:app",
        host="0.0.0.0",
        port=8000,
        reload=False,
        loop="asyncio"
    )

if __name__ == "__main__":
    main()

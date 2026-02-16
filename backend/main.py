import sys
import os
import asyncio

# Set policy GLOBALLY for all processes (including Uvicorn workers)
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    print("✅ WindowsProactorEventLoopPolicy set globally.")

from fastapi import FastAPI
from contextlib import asynccontextmanager
import uvicorn
from fastapi.middleware.cors import CORSMiddleware
from routers import agent as agent_router
from routers import tools as tools_router
from routers import events as events_router

# Voice dictation (simple, local)
from api import dictation

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup logic
    print("Startup: Connecting to services...")
    print("✅ Voice dictation ready (Faster-Whisper)")
    yield
    # Shutdown logic
    print("Shutdown: Closing connections...")

app = FastAPI(lifespan=lifespan)

# Allow CORS for Frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173", "http://127.0.0.1:8000"],  # Include self for desktop mode
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(agent_router.router)
app.include_router(tools_router.router)
app.include_router(events_router.router)
app.include_router(dictation.router)  # Simple voice dictation


@app.get("/")
async def read_root():
    return {"status": "online", "service": "AI Agent Backend"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

# --- Web Orchestration Endpoint ---
from pydantic import BaseModel

# --- Static Frontend Serving (Desktop Mode) ---
# When bundled as .exe, the frontend is embedded in static_frontend/
_FRONTEND_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static_frontend")
if os.path.isdir(_FRONTEND_DIR):
    from fastapi.staticfiles import StaticFiles
    from fastapi.responses import FileResponse

    # Serve Next.js _next/ assets
    _next_dir = os.path.join(_FRONTEND_DIR, "_next")
    if os.path.isdir(_next_dir):
        app.mount("/_next", StaticFiles(directory=_next_dir), name="next_assets")

    # SPA fallback: serve index.html for any unmatched route
    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        file_path = os.path.join(_FRONTEND_DIR, full_path)
        if os.path.isfile(file_path):
            return FileResponse(file_path)
        return FileResponse(os.path.join(_FRONTEND_DIR, "index.html"))

    print(f"🖥️  Desktop Mode: Serving frontend from {_FRONTEND_DIR}")


if __name__ == "__main__":
    is_desktop = "--desktop" in sys.argv or getattr(sys, 'frozen', False)
    uvicorn.run(
        "main:app",
        host="127.0.0.1" if is_desktop else "0.0.0.0",
        port=8000,
        reload=not is_desktop,
        loop="asyncio"
    )

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

# Allow CORS for Frontend (including Tauri desktop origins)
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
app.include_router(dictation.router)  # Simple voice dictation


@app.get("/")
async def read_root():
    return {"status": "online", "service": "AI Agent Backend"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        loop="asyncio"
    )

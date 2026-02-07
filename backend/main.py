from fastapi import FastAPI
from contextlib import asynccontextmanager
import uvicorn
from fastapi.middleware.cors import CORSMiddleware
from routers import agent as agent_router
from routers import tools as tools_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup logic (e.g., connect to Temporal, Weaviate)
    print("Startup: Connecting to services...")
    yield
    # Shutdown logic
    print("Shutdown: Closing connections...")

app = FastAPI(lifespan=lifespan)

# Allow CORS for Frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(agent_router.router)
app.include_router(tools_router.router)


@app.get("/")
async def read_root():
    return {"status": "online", "service": "AI Agent Backend"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)

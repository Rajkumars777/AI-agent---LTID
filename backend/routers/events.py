from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from typing import List, Dict, Any
import json
import asyncio

router = APIRouter(prefix="/ws", tags=["events"])

class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, List[WebSocket]] = {}

    async def connect(self, task_id: str, websocket: WebSocket):
        await websocket.accept()
        if task_id not in self.active_connections:
            self.active_connections[task_id] = []
        self.active_connections[task_id].append(websocket)
        print(f"WS: Client connected to task {task_id}")

    def disconnect(self, task_id: str, websocket: WebSocket):
        if task_id in self.active_connections:
            self.active_connections[task_id].remove(websocket)
            if not self.active_connections[task_id]:
                del self.active_connections[task_id]
        print(f"WS: Client disconnected from task {task_id}")

    async def send_event(self, task_id: str, event_type: str, data: Any):
        if task_id in self.active_connections:
            message = {
                "task_id": task_id,
                "type": event_type,
                "data": data,
                "timestamp": asyncio.get_event_loop().time()
            }
            # Broadcast to all connected clients for this task
            for connection in self.active_connections[task_id]:
                try:
                    await connection.send_text(json.dumps(message))
                except Exception as e:
                    print(f"WS: Error sending message: {e}")

manager = ConnectionManager()

@router.websocket("/{task_id}")
async def websocket_endpoint(websocket: WebSocket, task_id: str):
    await manager.connect(task_id, websocket)
    try:
        while True:
            # Keep connection alive, can handle client-to-server messages here if needed
            data = await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(task_id, websocket)

async def emit_event(task_id: str, event_type: str, data: Any):
    """Utility to emit events from anywhere in the backend."""
    await manager.send_event(task_id, event_type, data)

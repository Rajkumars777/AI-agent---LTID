import asyncio
import os
import sys

# Add src to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '.')))

from src.core.agent import run_agent

async def verify():
    query = "send 'hi' to 'AKKA' in whatsapp"
    print(f"🚀 Running WhatsApp verification: {query}")
    
    # Mock emit_event
    async def mock_emit(task_id, event, data):
        print(f"📡 [EVENT] {event}: {data}")

    # Patch emit_event in agent.py and orchestrator.py if necessary?
    # Actually, run_agent in agent.py uses app.ainvoke which calls execute_tool.
    # execute_tool gets emit_event from src.api.routers.events.
    # For a local verification script, I might need to patch it.
    
    import src.api.routers.events
    src.api.routers.events.emit_event = mock_emit

    try:
        result = await run_agent(query, task_id="verify-whatsapp")
        print("\n✅ Verification Result:")
        for step in result.get("steps", []):
            print(f"- [{step.get('timestamp')}] {step.get('tool')}: {step.get('content')}")
    except Exception as e:
        print(f"❌ Verification failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(verify())

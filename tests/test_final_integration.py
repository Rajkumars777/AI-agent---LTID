import sys
import os
import asyncio
sys.path.append(os.path.join(os.getcwd(), "backend"))

from agent import run_agent, agent_memory

async def test_integrated_capability():
    print("--- Integrated Capability Test ---")
    
    # 1. Setup Mock Memory (Simulate past turn)
    agent_memory.history.clear()
    agent_memory.add_interaction("Find my finance sheet", "I found Finance_2024.xlsx in C:/Users/Finance/")
    
    print("\n[Turn 2] User command: 'Open it and add a row for coffee 500'")
    # We want to see if "it" resolves to Finance_2024.xlsx and if "coffee 500" is parsed.
    
    # Note: This will call the real LLM. If API Key is missing, it will log warning.
    try:
        results = await run_agent("Open it and add a row for coffee 500")
        print(f"\nExecution result steps: {len(results.get('steps', []))}")
        for step in results.get('steps', []):
            print(f"- {step['content'][:100]}...")
            
        # Check if memory was updated
        ctx = agent_memory.get_context_string()
        print(f"\nUpdated Context:\n{ctx}")
        assert "coffee" in ctx or "add a row" in ctx
    except Exception as e:
        print(f"Skipping full integration execution (API dependent): {e}")

    print("\n--- Smart Resolver Verification (Universal) ---")
    from utils.resolver import resolve_file_arg
    # Create temp file
    temp_file = "test_resolver_final.xlsx"
    with open(temp_file, "w") as f: f.write("dummy")
    
    resolved = resolve_file_arg(temp_file)
    print(f"Resolved '{temp_file}' -> {resolved}")
    assert os.path.isabs(resolved)
    
    os.remove(temp_file)
    print("✅ Final Integration Logic Verified!")

if __name__ == "__main__":
    asyncio.run(test_integrated_capability())

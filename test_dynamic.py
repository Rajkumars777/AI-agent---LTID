import asyncio
import sys
import os
sys.path.append(os.getcwd())
try:
    from src.tools.generator import generator, dynamic_s1_automation
except ImportError as e:
    print(f"ImportError: {e}")
    sys.exit(1)

async def test():
    query = 'create a pdf HOO.pdf with a content of "HI"'
    print("Testing dynamic S1 generator for query:", query)
    
    # 1. Generate Code
    code = await dynamic_s1_automation._generate_code(query)
    print("\n--- GENERATED CODE ---")
    print(code)
    print("----------------------")
    
    if not code:
        print("Failed to generate code!")
        return

    # 2. Validate
    is_valid, issues = dynamic_s1_automation._validate_code(code)
    print(f"Valid: {is_valid}, Issues: {issues}")
    
    # 3. Simulate execution
    if is_valid:
        params = dynamic_s1_automation._extract_params(query)
        print(f"\nExtracted Params: {params}")
        result = dynamic_s1_automation._execute(code, params)
        print(f"\nExecution Result:\n{result}")

asyncio.run(test())

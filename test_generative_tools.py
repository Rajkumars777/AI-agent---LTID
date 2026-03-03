import asyncio
import os
import sys
import dspy
from dotenv import load_dotenv

# Add root to sys.path
root_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(root_dir)

# Load environment variables
load_dotenv()

# Configure DSPy
groq_key = os.getenv("GROQ_API_KEY")
if groq_key:
    lm = dspy.LM("groq/llama-3.3-70b-versatile", api_key=groq_key)
    dspy.configure(lm=lm)
    print("DSPy configured with Groq")
else:
    or_key = os.getenv("OPENROUTER_API_KEY")
    if or_key:
        lm = dspy.LM("google/gemini-2.0-flash-001", api_key=or_key, api_base="https://openrouter.ai/api/v1")
        dspy.configure(lm=lm)
        print("DSPy configured with OpenRouter")
    else:
        print("Error: No API key found in .env")
        sys.exit(1)

from src.core.intelligence.code_generator import generate_and_run_script

task = "create a new Book1.xlsx in Downloads, then put the value of 1,2,3,4,5 from A1 vertically and calculate the total , average and standard deviation of A1 column . And create a pp1.pptx in Downlods and input those 3 calculation into the pp1.pptx ."
file_path = "auto"

print(f"Executing task: {task}")
result = generate_and_run_script(task, file_path)
print("\nRESULT:\n")
print(result)

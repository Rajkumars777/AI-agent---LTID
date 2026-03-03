import ast
import re
from src.tools.generator import generator

# Test extracting string from typical LLM output
code_text = """
def execute(params: dict) -> str:
    try:
        from reportlab.pdfgen import canvas
        import os

        file_name = params.get("target", "HOO.pdf")
        content = params.get("message", "HI")
        
        # Open the generated PDF
        return f"[Success] PDF created"

    except Exception as e:
        return f"[Error] Failed to create PDF: {str(e)}"
"""

print(generator._clean_llm_output("```python" + code_text + "```"))

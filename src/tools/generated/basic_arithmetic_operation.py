"""
Auto-generated tool: basic_arithmetic_operation
Do not edit manually.
"""

import os

def execute(params: dict) -> str:
    try:
        num1 = float(params.get("num1", 0))
        operator = params.get("operator", "+")
        num2 = float(params.get("num2", 0))

        if operator == "+":
            result = num1 + num2
        elif operator == "-":
            result = num1 - num2
        elif operator == "*":
            result = num1 * num2
        elif operator == "/":
            if num2 != 0:
                result = num1 / num2
            else:
                return "[Error] Division by zero"
        else:
            return "[Error] Invalid operator"

        return f"[Success] Result: {result}"
    except Exception as e:
        return f"[Error] {str(e)}"
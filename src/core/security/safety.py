import ast
from typing import List, Tuple

class SafetyViolation(Exception):
    """Raised when dangerous code is detected."""
    pass

# Whitelist of allowed modules
# NOTE:
# - We allow powerful libraries (os, win32com, pdf/Word libs) but still block
#   dangerous *operations* below via DANGEROUS_CALLS.
ALLOWED_MODULES = {
    'pandas', 'pd', 'openpyxl', 'math', 'json', 'datetime',
    're', 'string', 'collections', 'itertools', 'numpy', 'np',
    'os', 'tempfile', 'io', 'sys', 'time', 'csv',
    # Data retrieval / web
    'yfinance', 'yf', 'requests', 'bs4', 'urllib',
    # Date/time
    'dateutil', 'pytz', 'calendar',
    # Document / PDF intelligence
    'pymupdf',      # PyMuPDF
    'fitz',         # Alternate import name for PyMuPDF
    'pdfplumber',
    'docx',         # python-docx
    # Windows Office automation (for Save As / format conversions)
    'win32com',     # win32com.client
    'pythoncom',
}

# Blacklist of dangerous functions/attributes
# Note: 'os' is allowed in modules, but we block specific 'os' functions
DANGEROUS_CALLS = {
    'system', 'popen', 'subprocess', 'spawn', 'fork', 'exec', 'eval',
    'rmtree', 'remove', 'unlink', 'rename', 'chmod', 'chown',
    'kill', 'terminate'
}

def validate_code(code: str) -> Tuple[bool, str]:
    """
    Analyzes Python code using AST to check for safety violations.
    Returns (is_safe, message).
    """
    try:
        tree = ast.parse(code)
    except SyntaxError as e:
        return False, f"Syntax Error: {str(e)}"

    for node in ast.walk(tree):
        # 1. Check Imports
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.split('.')[0] not in ALLOWED_MODULES:
                    return False, f"Forbidden import: {alias.name}"
        
        elif isinstance(node, ast.ImportFrom):
            if node.module and node.module.split('.')[0] not in ALLOWED_MODULES:
                return False, f"Forbidden import from: {node.module}"

        # 2. Check Function Calls (Attribute calls like os.system)
        elif isinstance(node, ast.Call):
            func = node.func
            
            # Simple calls like eval()
            if isinstance(func, ast.Name):
                if func.id in DANGEROUS_CALLS:
                    return False, f"Dangerous function call: {func.id}()"
            
            # Attribute calls like os.system()
            elif isinstance(func, ast.Attribute):
                if func.attr in DANGEROUS_CALLS:
                    return False, f"Dangerous operation: {func.attr}"
                    
        # 3. Prevent direct access to dangerous built-ins via getattr/setattr
        elif isinstance(node, (ast.Attribute, ast.Name)):
            name = node.id if isinstance(node, ast.Name) else node.attr
            if name == "__subclasses__" or name == "__globals__":
                 return False, f"Forbidden attribute access: {name}"

    return True, "Code verified as safe."

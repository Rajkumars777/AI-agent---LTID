import sys
import os
import subprocess

# Ensure backend is in path
sys.path.append(os.path.abspath("backend"))

from capabilities.desktop_ops import resolve_target_path
from tools.core_tools import initialize_core_tools

def get_uwp_apps(query):
    """Try to find UWP app ID via PowerShell"""
    try:
        ps_script = f"Get-StartApps | Where-Object {{ $_.Name -like '*{query}*' }} | Select-Object -First 1 Name, AppID | ConvertTo-Json"
        cmd = ["powershell", "-NoProfile", "-Command", ps_script]
        result = subprocess.run(cmd, capture_output=True, text=True)
        return result.stdout.strip()
    except Exception as e:
        return str(e)

if __name__ == "__main__":
    target = "WhatsApp"
    print(f"Resolving '{target}'...")
    
    # Check current resolution path
    path = resolve_target_path(target)
    print(f"Result: {path}")
    
    if path and path.startswith("VISUAL_RPA"):
        print("\n[Debug] Fallback to Visual RPA confirmed.")
        print("Checking if UWP App exists via PowerShell...")
        uwp_info = get_uwp_apps(target)
        print(f"UWP Info: {uwp_info}")

"""
Build Script — AI Agent Desktop
==================================
Automates the full build pipeline:
  1. Build React frontend → static files
  2. Copy to backend/static_frontend/
  3. Run PyInstaller to create .exe

Usage:
    python build.py
"""

import os
import sys
import shutil
import subprocess

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
FRONTEND_DIR = os.path.join(ROOT_DIR, "frontend")
BACKEND_DIR = os.path.join(ROOT_DIR, "backend")
STATIC_DIR = os.path.join(BACKEND_DIR, "static_frontend")
SPEC_FILE = os.path.join(ROOT_DIR, "build_desktop.spec")

def step(msg):
    print(f"\n{'='*50}")
    print(f"  {msg}")
    print(f"{'='*50}\n")

def run(cmd, cwd=None):
    print(f"  > {cmd}")
    result = subprocess.run(cmd, shell=True, cwd=cwd or ROOT_DIR)
    if result.returncode != 0:
        print(f"  ❌ FAILED (exit code {result.returncode})")
        sys.exit(1)

def main():
    # ── Step 1: Build Frontend ──
    step("Step 1: Building React Frontend")
    run("npm run build", cwd=FRONTEND_DIR)

    # ── Step 2: Copy to backend ──
    step("Step 2: Copying frontend to backend/static_frontend/")
    if os.path.exists(STATIC_DIR):
        shutil.rmtree(STATIC_DIR)
    shutil.copytree(os.path.join(FRONTEND_DIR, "out"), STATIC_DIR)
    file_count = sum(len(files) for _, _, files in os.walk(STATIC_DIR))
    print(f"  ✅ Copied {file_count} files")

    # ── Step 3: PyInstaller ──
    step("Step 3: Building .exe with PyInstaller")
    run(f"pyinstaller \"{SPEC_FILE}\" --noconfirm", cwd=ROOT_DIR)

    # ── Done ──
    exe_path = os.path.join(ROOT_DIR, "dist", "AI-Agent.exe")
    if os.path.exists(exe_path):
        size_mb = os.path.getsize(exe_path) / (1024 * 1024)
        step(f"✅ BUILD COMPLETE!")
        print(f"  Output: {exe_path}")
        print(f"  Size:   {size_mb:.1f} MB")
    else:
        step("⚠️ Build finished but .exe not found at expected location")
        print(f"  Check the dist/ directory for the output")

if __name__ == "__main__":
    main()


import sys
import os
import uvicorn
import multiprocessing

# Verify we are running in a frozen bundle (PyInstaller)
if getattr(sys, 'frozen', False):
    # If the application is run as a bundle, the PyInstaller bootloader
    # extends the sys module by a flag frozen=True and sets the app 
    # path into variable _MEIPASS'.
    base_dir = sys._MEIPASS
    
    # Set CWD to the directory containing the exe so relative paths work
    exe_dir = os.path.dirname(os.path.abspath(sys.executable))
    os.chdir(exe_dir)
else:
    base_dir = os.path.dirname(os.path.abspath(__file__))

# Set environment variables
os.environ["FROZEN_APP_PATH"] = base_dir

# Load .env from the bundle (PyInstaller _MEIPASS) or from CWD
from dotenv import load_dotenv

# Try loading from bundled location first, then from CWD
env_path_bundle = os.path.join(base_dir, '.env')
env_path_cwd = os.path.join(os.getcwd(), '.env')
env_path_exe = os.path.join(os.path.dirname(os.path.abspath(sys.executable)), '.env') if getattr(sys, 'frozen', False) else None

for env_path in [env_path_bundle, env_path_cwd, env_path_exe]:
    if env_path and os.path.exists(env_path):
        load_dotenv(env_path)
        print(f"✅ Loaded .env from: {env_path}")
        break
else:
    print("⚠️ WARNING: No .env file found! API keys will be missing.")

if __name__ == "__main__":
    # Required for PyInstaller to work with multiprocessing
    multiprocessing.freeze_support()
    
    # Add the base directory to sys.path so local imports resolve
    if base_dir not in sys.path:
        sys.path.insert(0, base_dir)
    
    try:
        from main import app
        
        print(f"🚀 Starting AI Engine backend on 127.0.0.1:8000...")
        print(f"   Base dir: {base_dir}")
        print(f"   CWD: {os.getcwd()}")
        print(f"   Frozen: {getattr(sys, 'frozen', False)}")
        
        # Run the server
        # We use strict Host/Port matching what the Frontend expects
        uvicorn.run(app, host="127.0.0.1", port=8000, log_level="info")
        
    except Exception as e:
        import traceback
        print(f"❌ Failed to start backend: {e}")
        traceback.print_exc()
        # Keep window open on error if running in console
        if getattr(sys, 'frozen', False):
            input("Press Enter to exit...")

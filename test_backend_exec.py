
import subprocess
import time
import requests
import sys
import os

def test_backend_executable():
    executable_path = os.path.abspath("backend/dist/ai-engine.exe")
    if not os.path.exists(executable_path):
        print(f"Error: Executable not found at {executable_path}")
        return False

    print(f"Launching {executable_path}...")
    # Launch the process
    process = subprocess.Popen(
        [executable_path],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )

    print("Waiting for backend to start (10s)...")
    time.sleep(10)

    try:
        # Check health endpoint
        response = requests.get("http://127.0.0.1:8000/health")
        if response.status_code == 200:
            print("✅ Backend Health Check Passed!")
            print(f"Response: {response.json()}")
            success = True
        else:
            print(f"❌ Backend Health Check Failed with status {response.status_code}")
            success = False
    except requests.exceptions.ConnectionError:
        print("❌ Could not connect to backend (Connection refused)")
        success = False
    except Exception as e:
        print(f"❌ Error during verification: {e}")
        success = False
    finally:
        print("Terminating backend process...")
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
        
        # Print logs if failed
        if not success:
            stdout, stderr = process.communicate()
            print("--- STDOUT ---")
            print(stdout)
            print("--- STDERR ---")
            print(stderr)

    return success

if __name__ == "__main__":
    if test_backend_executable():
        sys.exit(0)
    else:
        sys.exit(1)

import subprocess
import sys
import time
import os

def check_game():
    print("Starting game check...")
    
    # Path to the python executable in the venv
    python_exe = os.path.join("venv", "Scripts", "python.exe")
    if not os.path.exists(python_exe):
        # Fallback for other OS or if venv is in a different place
        python_exe = "python"

    try:
        # Run main.py with a timeout of 3 seconds
        # We use a short timeout because if the window opens and doesn't crash immediately,
        # it's likely working for the basic initialization.
        process = subprocess.Popen(
            [python_exe, "main.py"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        try:
            # Wait for 3 seconds
            stdout, stderr = process.communicate(timeout=5)
            # If it reaches here, it means the process exited on its own (likely an error)
            print("Game exited unexpectedly.")
            print("STDOUT:", stdout)
            print("STDERR:", stderr)
            return False
        except subprocess.TimeoutExpired:
            # This is the SUCCESS case
            print("Game reached timeout without crashing. Success!")
            process.kill()
            return True
            
    except Exception as e:
        print(f"An error occurred while running the check: {e}")
        return False

if __name__ == "__main__":
    success = check_game()
    if not success:
        sys.exit(1)
    else:
        sys.exit(0)

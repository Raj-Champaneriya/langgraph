#!/usr/bin/env python3
import subprocess
import sys
import os

def main():
    file_to_run = sys.argv[1]
    
    # Run mypy
    mypy_result = subprocess.run(['mypy', file_to_run])
    
    # If mypy passes, run the script
    if mypy_result.returncode == 0:
        print(f"\n--- Mypy check passed. Running {file_to_run} ---\n")
        os.execvp('python', ['python', file_to_run])
    else:
        print("\n--- Mypy check failed. Fix type errors before running. ---")
        sys.exit(1)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python run_with_mypy.py <python_file>")
        sys.exit(1)
    main()
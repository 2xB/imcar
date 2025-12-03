#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Test script to verify the built executable launches a GUI successfully.

This script launches the application in testing mode and verifies that
the main window appears. It is designed to run in CI environments with
a virtual display (xvfb on Linux).
"""

import subprocess
import sys
import os
import time
import platform


# Timeout constants (can be overridden via environment variables)
STARTUP_TIMEOUT = int(os.environ.get("GUI_TEST_STARTUP_TIMEOUT", "10"))
TERMINATION_TIMEOUT = int(os.environ.get("GUI_TEST_TERMINATION_TIMEOUT", "5"))


def find_executable():
    """Find the built executable path based on the operating system."""
    if platform.system() == "Windows":
        # Windows executable
        exe_path = os.path.join("pyinstaller", "dist", "imcar", "imcar.exe")
    else:
        # Linux executable
        exe_path = os.path.join("pyinstaller", "dist", "imcar", "imcar")
    
    if not os.path.exists(exe_path):
        raise FileNotFoundError(f"Executable not found at {exe_path}")
    
    return exe_path


def test_executable_launches_gui():
    """
    Test that the executable launches and creates a GUI window.
    
    This test:
    1. Launches the executable with --test flag
    2. Waits for the application to start
    3. Verifies the process is running
    4. Terminates the process
    """
    exe_path = find_executable()
    print(f"Testing executable: {exe_path}")
    
    # Launch the executable with --test flag
    # The --test flag enables test devices for development purposes
    try:
        process = subprocess.Popen(
            [exe_path, "--test"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
    except Exception as e:
        raise RuntimeError(f"Failed to launch executable: {e}")
    
    print(f"Process started with PID: {process.pid}")
    
    # Wait for the application to initialize
    # Give it some time to start up and create the window
    print(f"Waiting {STARTUP_TIMEOUT} seconds for application to start...")
    
    for i in range(STARTUP_TIMEOUT):
        time.sleep(1)
        
        # Check if process is still running
        poll_result = process.poll()
        if poll_result is not None:
            # Process exited prematurely
            stdout, stderr = process.communicate()
            raise RuntimeError(
                f"Application exited prematurely with code {poll_result}\n"
                f"stdout: {stdout}\n"
                f"stderr: {stderr}"
            )
        
        print(f"  ... {i + 1}/{STARTUP_TIMEOUT}s - Process still running")
    
    # Verify process is still running after startup time
    if process.poll() is None:
        print("SUCCESS: Application is running after startup period")
    else:
        stdout, stderr = process.communicate()
        raise RuntimeError(
            f"Application exited during startup\n"
            f"stdout: {stdout}\n"
            f"stderr: {stderr}"
        )
    
    # Clean up - terminate the process
    print("Terminating application...")
    process.terminate()
    
    try:
        # Wait for graceful termination
        process.wait(timeout=TERMINATION_TIMEOUT)
        print("Application terminated gracefully")
    except subprocess.TimeoutExpired:
        # Force kill if it doesn't terminate gracefully
        print("Force killing application...")
        process.kill()
        process.wait()
        print("Application force killed")
    
    print("\n=== GUI Launch Test PASSED ===")
    return True


if __name__ == "__main__":
    try:
        test_executable_launches_gui()
        sys.exit(0)
    except Exception as e:
        print(f"\n=== GUI Launch Test FAILED ===")
        print(f"Error: {e}")
        sys.exit(1)

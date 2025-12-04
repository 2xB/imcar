#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Test script to verify the built executable launches a GUI successfully.

This script launches the application in testing mode and verifies that
the main window appears by checking for the shell server that starts
when the GUI is created. It is designed to run in CI environments with
a virtual display (xvfb on Linux).
"""

import subprocess
import sys
import os
import time
import platform
import socket
import urllib.request
import urllib.error


# Timeout constants (can be overridden via environment variables)
STARTUP_TIMEOUT = int(os.environ.get("GUI_TEST_STARTUP_TIMEOUT", "30"))
TERMINATION_TIMEOUT = int(os.environ.get("GUI_TEST_TERMINATION_TIMEOUT", "5"))

# Port used by the shell server (started when GUI opens)
SHELL_SERVER_PORT = 40405


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


def check_gui_server_running():
    """
    Check if the GUI's shell server is running by attempting to connect.
    
    The iMCAr application starts a web server on port 40405 when the GUI
    opens. This is a reliable way to verify the GUI has actually started.
    
    Returns:
        bool: True if the server is responding, False otherwise
    """
    try:
        # Try to connect to the shell server
        url = f"http://localhost:{SHELL_SERVER_PORT}/"
        with urllib.request.urlopen(url, timeout=2) as response:
            # If we get any response, the server is running
            return response.status == 200
    except (urllib.error.URLError, socket.timeout, ConnectionRefusedError, OSError):
        return False


def test_executable_launches_gui():
    """
    Test that the executable launches and creates a GUI window.
    
    This test:
    1. Launches the executable with --test flag
    2. Waits for the GUI's shell server to become available on port 40405
    3. Verifies the server responds (proving GUI has opened)
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
    
    # Wait for the GUI's shell server to become available
    # The shell server starts when the main window is created
    print(f"Waiting up to {STARTUP_TIMEOUT}s for GUI shell server on port {SHELL_SERVER_PORT}...")
    
    gui_opened = False
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
        
        # Check if GUI server is responding
        if check_gui_server_running():
            print(f"  ... {i + 1}s - GUI shell server is responding!")
            gui_opened = True
            break
        else:
            print(f"  ... {i + 1}/{STARTUP_TIMEOUT}s - Waiting for GUI...")
    
    if not gui_opened:
        # Process is still running but GUI server never responded
        stdout_partial = ""
        stderr_partial = ""
        try:
            process.terminate()
            stdout_partial, stderr_partial = process.communicate(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()
        except Exception:
            # Handle any other cleanup errors
            process.kill()
            process.wait()
        
        raise RuntimeError(
            f"GUI shell server did not respond within {STARTUP_TIMEOUT}s.\n"
            f"The application is running but the GUI may not have opened.\n"
            f"stdout: {stdout_partial}\n"
            f"stderr: {stderr_partial}"
        )
    
    print("SUCCESS: GUI has opened and shell server is responding")
    
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

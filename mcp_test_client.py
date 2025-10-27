"""
MCP test client for DShield MCP server.

This module provides a test client for the DShield MCP server.
"""

import json
import subprocess
import threading


def read_stdout(proc) -> None:
    """Read stdout from the process and print it."""
    for line in proc.stdout:
        print("SERVER:", line.rstrip())


def main() -> None:
    """Main function to run the MCP test client."""
    # Start the MCP server as a subprocess in text mode
    proc = subprocess.Popen(
        ["python", "mcp_server.py"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,  # <-- This is key!
        bufsize=1,
    )

    # Start a thread to read server output
    threading.Thread(target=read_stdout, args=(proc,), daemon=True).start()

    # Example: List tools
    request = {"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}}
    proc.stdin.write(json.dumps(request) + "\n")
    proc.stdin.flush()

    # Wait for a bit to see the response
    import time

    time.sleep(2)

    # Clean up
    proc.terminate()


if __name__ == "__main__":
    main()

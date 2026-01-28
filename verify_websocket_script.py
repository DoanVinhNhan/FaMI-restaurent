
import asyncio
import json
import websockets
import os
import sys

# Add project root to path
sys.path.append(os.getcwd())

async def listen_to_kitchen():
    # Attempt to connect to the running daphne server on default port 8000
    uri = "ws://127.0.0.1:8000/ws/notifications/kitchen/"
    print(f"Connecting to {uri}...")
    
    try:
        async with websockets.connect(uri) as websocket:
            print("Connected! Waiting for messages (10s timeout)...")
            
            # Wait for a message with timeout
            try:
                message = await asyncio.wait_for(websocket.recv(), timeout=10.0)
                data = json.loads(message)
                print(f"\n[Kitchen Display] Received Notification:")
                print(json.dumps(data, indent=2))
                return True
            except asyncio.TimeoutError:
                print("No message received in 10s.")
                return False
                
    except Exception as e:
        print(f"Connection failed: {e}")
        return False

# Since creating a subprocess for the server is complex within this environment,
# We will assume the USER is running the server (as requested in plan), 
# OR we will simulate the send in a separate thread if possible,
# BUT effectively 'runserver' must be running.
# 
# For this automated check, we will just CREATE the file for the user to use 
# or try a quick connect check if port is open.

import asyncio
import websockets
import json
import http.server
import socketserver
import threading
import os
import time
import socket

# Editor Configuration
HTTP_PORT = 8080
WS_PORT = 8081
EDITOR_DIR = os.path.join(os.path.dirname(__file__), 'editor')

# Simple HTTP Server to host the web app
class RequestHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=EDITOR_DIR, **kwargs)

def start_http_server():
    with socketserver.TCPServer(("", HTTP_PORT), RequestHandler) as httpd:
        print(f"[*] Web Editor gestart op: http://localhost:{HTTP_PORT}")
        httpd.serve_forever()

# WebSocket Server for 2-way communication
connected_clients = set()

async def handler(websocket, *args):
    connected_clients.add(websocket)
    print("[*] Web Editor client verbonden via WebSocket!")
    try:
        async for message in websocket:
            data = json.loads(message)
            print(f"[WS] Ontvangen: {data}")
            # TODO: Add specific action parsing (e.g. skip time, send test color)
            
    except websockets.exceptions.ConnectionClosed:
        print("[-] Client disconnected.")
    finally:
        connected_clients.remove(websocket)

async def broadcast(message_dict):
    if connected_clients:
        msg = json.dumps(message_dict)
        await asyncio.gather(*[client.send(msg) for client in connected_clients])

async def main_ws():
    print(f"[*] WebSocket bridge luistert op poort {WS_PORT}")
    async with websockets.serve(handler, "localhost", WS_PORT):
        await asyncio.Future()  # Run forever

if __name__ == "__main__":
    if not os.path.exists(EDITOR_DIR):
        os.makedirs(EDITOR_DIR)
        print(f"[*] Map {EDITOR_DIR} aangemaakt.")
    
    # Start HTTP server in a separate thread so it doesn't block asyncio
    http_thread = threading.Thread(target=start_http_server, daemon=True)
    http_thread.start()
    
    # Give it a tiny delay to print nicely
    time.sleep(0.5)
    
    # Start WebSocket loop
    try:
        asyncio.run(main_ws())
    except KeyboardInterrupt:
        print("\n[*] Bridge afgesloten.")

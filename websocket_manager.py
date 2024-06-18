from models.game import Game
import asyncio
from starlette.websockets import WebSocketState
import asyncio
from models.game import Game
import json

class WebSocketManager:
    def __init__(self):
        self.active_websockets = {}
        self.game_websockets = {}  # Assuming you have a separate list for game-specific sockets

    async def add_websocket(self, websocket):
        game_info = await Game.currentGameInfo()  # Ensure you await the method
        if game_info:
            await websocket.send_text(json.dumps(game_info))  # Serialize to JSON string
        self.active_websockets[id(websocket)] = websocket

    async def broadcast(self, message: str, game_only=False):
        target_websockets = self.game_websockets if game_only else self.active_websockets
        disconnected_websockets = []
        for websocket_id, websocket in list(target_websockets.items()):
            if websocket.client_state == WebSocketState.DISCONNECTED:
                disconnected_websockets.append(websocket_id)
                continue
            try:
                await websocket.send_text(message)  # Ensure message is a string
            except Exception as e:
                disconnected_websockets.append(websocket_id)
                print(f"Failed to send message, error: {e}")

        for websocket_id in disconnected_websockets:
            self.remove_websocket(target_websockets[websocket_id])

    def remove_websocket(self, websocket):
        """Remove a WebSocket from both general and game-specific lists."""
        websocket_id = id(websocket)
        if websocket_id in self.active_websockets:
            del self.active_websockets[websocket_id]
        if websocket_id in self.game_websockets:
            del self.game_websockets[websocket_id]

    async def broadcast_game_info_every_5_seconds(self):
        while True:
            await asyncio.sleep(5)
            game_info = await Game.currentGameInfo()  # Ensure you await the method
            if game_info:
                print("Broadcasting game info")
                await self.broadcast(json.dumps(game_info), game_only=True)  # Serialize to JSON string

    def start_broadcasting(self):
        asyncio.create_task(self.broadcast_game_info_every_5_seconds())

# Create a global WebSocket manager instance
websocket_manager = WebSocketManager()
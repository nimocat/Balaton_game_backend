import aioredis
from models.game import Game
import asyncio
from starlette.websockets import WebSocketState
import asyncio
from database import redis_client
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

    async def add_websocket_to_game(self, websocket, player_name) -> bool:
        """Add a WebSocket to the game-specific list if it is already active and update game_websockets."""
        try:
            websocket_id = id(websocket)
            if websocket_id in self.active_websockets:
                current_game_id = redis_client.get("CURRENT_GAME").decode('utf-8')
                sockets_key = f"{current_game_id}_SOCKETS"
                redis_client.hset(sockets_key, websocket_id, player_name)
                self.game_websockets[websocket_id] = websocket
                print(f"[Enter Game] Player {player_name} with Socket ID {websocket_id} recorded")
                print(f"[Game Sockets] {self.game_websockets}")
            return True
        except Exception as e:
            print(f"Error adding websocket to game: {e}")
            return False

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
            print('game socket has been deleted')
            del self.game_websockets[websocket_id]

    async def broadcast_game_info_every_5_seconds(self):
        while True:
            await asyncio.sleep(1)
            game_info = await Game.currentGameInfo()  # Ensure you await the method
            if game_info:
                wrapped_message = json.dumps({"type": "game_info", "data": game_info})
                await self.broadcast(wrapped_message, game_only=False)  # Serialize to JSON string

    def start_broadcasting(self):
        asyncio.create_task(self.broadcast_game_info_every_5_seconds())
        asyncio.create_task(self.subscribe_and_broadcast_game_result())

    async def subscribe_and_broadcast_game_result(self):
        try:
            redis = await aioredis.from_url("redis://localhost", encoding="utf-8", decode_responses=True)
            pubsub = redis.pubsub()
            await pubsub.subscribe('endgameinfo')
            print("[Subscribed] Listening to 'endgameinfo' channel for game results.")

            async for message in pubsub.listen():
                if message['type'] == 'message':
                    game_id = message['data']
                    print(f"[Results Broadcasting] Game ID received: {game_id}")

                    sockets_key = f"{game_id}_SOCKETS"
                    all_sockets = await redis.hgetall(sockets_key)

                    for socket_id, player_name in all_sockets.items():
                        try:
                            game_info_response = await Game.getEndedGameInfo(game_id, player_name)
                            data = {"type": "ended_game_info", "data": game_info_response.dict()}
                            print("game_websockets contents:", self.game_websockets)
                            print("active_websockets contents:", self.active_websockets)
                            websocket = self.game_websockets.pop(int(socket_id), None)
                            if websocket:
                                print(f"[Broadcasting] Broadcast to Player {player_name} with Socket ID {socket_id}")
                                await websocket.send_text(json.dumps(data))
                        except Exception as e:
                            print(f"Failed to fetch or send game info for {player_name} with Socket ID {socket_id}: {e}")
        except Exception as e:
            print(f"Error in subscribe_and_broadcast_game_result: {str(e)}")

    # async def start_broadcasting(self):
    #     # await self.broadcast_game_info_every_1_seconds()
    #     asyncio.create_task(self.broadcast_game_info_every_1_seconds())
    # async def start_websocket_manager(self):
    #     asyncio.create_task(self.start_broadcasting())
# Create a global WebSocket manager instance
websocket_manager = WebSocketManager()
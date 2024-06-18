from fastapi import WebSocket, APIRouter
from models.general import CurrentGameInfo
from database import redis_client
from websocket_manager import websocket_manager
from models.general import Game
import json

game_ws = APIRouter()

@game_ws.websocket("/ws/gameinfo")
async def websocket_gameinfo(websocket: WebSocket):
    await websocket.accept()
    await websocket_manager.add_websocket(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            if data == "request_gameinfo":
                game_info = await Game.currentGameInfo()  # Ensure you await the method
                await websocket.send_text(json.dumps(game_info))
            elif data == "disconnect":
                break
    finally:
        await websocket.close()
        websocket_manager.remove_websocket(websocket)
from aifc import Error
from fastapi import HTTPException, WebSocket, APIRouter
from game_logic import player_entrance
from models.game import CurrentGameInfo
from database import redis_client
from websocket_manager import websocket_manager
from models.game import Game
import json

game_ws = APIRouter()

@game_ws.websocket("/ws/game")
async def websocket_gameinfo(websocket: WebSocket):
    await websocket.accept()
    await websocket_manager.add_websocket(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            try:
                message = json.loads(data)
                message_type = message.get("type")
                message_data = message.get("data", {})

                match message_type:
                    case "request_gameinfo":
                        game_info = await Game.currentGameInfo()
                        await websocket.send_text(json.dumps({"type": "gameinfo", "data": game_info}))

                    case "entrance":
                        player_name = message_data.get("player_name")
                        payment = message_data.get("payment")
                        if not player_name or payment is None:
                            raise HTTPException(status_code=404, detail="Missing player_name or payment")

                        current_game_id = redis_client.get("CURRENT_GAME")
                        if current_game_id is None:
                            raise HTTPException(status_code=404, detail="No current game running.")
                        current_game_id = current_game_id.decode('utf-8')

                        hands_key = f"{current_game_id}_HANDS"
                        if redis_client.hexists(hands_key, player_name):
                            raise HTTPException(status_code=400, detail="Player already in the game.")

                        player_tokens_key = f"{player_name}_TOKENS"
                        player_tokens = redis_client.get(player_tokens_key)
                        if player_tokens is None or float(player_tokens) < payment:
                            raise HTTPException(status_code=400, detail="Insufficient tokens for entry.")

                        if payment == 20:
                            card_num = 2
                        elif payment == 40:
                            card_num = 3
                        else:
                            raise HTTPException(status_code=400, detail="Invalid payment amount")
                        print("entering game", player_name, payment)
                        cards = player_entrance(player_name, card_num)
                        if await websocket_manager.add_websocket_to_game(websocket, player_name):
                            await websocket.send_text(json.dumps({"type": "success", "data": {"cards": cards}}))
                    case "disconnect":
                        break

            except json.JSONDecodeError:
                await websocket.send_text(json.dumps({"type": "error", "data": "Invalid JSON format"}))
            except HTTPException as e:
                await websocket.send_text(json.dumps({"type": "error", "data": str(e.detail)}))
            except Exception as e:
                await websocket.send_text(json.dumps({"type": "error", "data": str(e)}))

    finally:
        await websocket.close()
        websocket_manager.remove_websocket(websocket)
from fastapi import WebSocket, APIRouter
from models import CurrentGameInfo
from database import redis_client
from websocket_manager import websocket_manager

game_ws = APIRouter()

@game_ws.websocket("/ws/gameinfo")
async def websocket_gameinfo(websocket: WebSocket):
    await websocket.accept()
    websocket_manager.add_websocket(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            if data == "request_gameinfo":
                await send_game_info(websocket)
            elif data == "disconnect":
                break
    finally:
        await websocket.close()
        websocket_manager.remove_websocket(websocket)

async def send_game_info(websocket):
    current_game_id = redis_client.get("CURRENT_GAME")
    if current_game_id:
        current_game_id = current_game_id.decode('utf-8')
        pool_key = f"{current_game_id}_POOL"
        pool_amount = redis_client.get(pool_key)
        pool_amount = int(pool_amount) if pool_amount else 0
        player_count_key = f"{current_game_id}_COUNT"
        player_count = redis_client.get(player_count_key)
        player_count = int(player_count) if player_count else 0
            # 计算当前游戏时间
        game_showtime = redis_client.ttl("CURRENT_GAME")
        game_info = CurrentGameInfo(
            game_id=current_game_id,
            pool_amount=pool_amount,
            player_amount=player_count,
            game_time=game_showtime  # Placeholder for game time, needs proper implementation
        )
        await websocket.send_json(game_info.dict())
    else:
        await websocket.send_text("No current game found.")
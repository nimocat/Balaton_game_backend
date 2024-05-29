from fastapi import FastAPI, APIRouter, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse
from database import db, serialize_objectid
from game_logic import current_game, current_game_lock
from pydantic import BaseModel
from database import redis_client
import asyncio
from datetime import datetime

router = APIRouter()

class PlayerResponse(BaseModel):
    game_id: str
    score: int
    hand: str
    pool: int

class CurrentGameInfo(BaseModel):
    game_id: str
    pool_amount: int
    player_amount: int
    game_time: str

class FullGameInfo(BaseModel):
    game_id: str
    pool_amount: int
    player_amount: int
    game_time: str
@router.get("/game_id", response_model=str)
async def get_current_game_id():

    # 获取当前游戏的ID
    current_game_id = redis_client.get("CURRENT_GAME")
    if current_game_id is None:
        raise HTTPException(status_code=404, detail="No current game found.")
    return current_game_id.decode('utf-8')

@router.get("/player/{player_name}/score", response_model=int)
async def get_player_score(player_name: str):

    # 获取当前游戏的ID
    current_game_id = redis_client.get("CURRENT_GAME")
    if current_game_id is None:
        raise HTTPException(status_code=404, detail="No current game found.")
    current_game_id = current_game_id.decode('utf-8')

    # 获取玩家本局游戏的分数
    scores_key = f"{current_game_id}_SCORES"
    player_score = redis_client.zscore(scores_key, player_name)
    if player_score is None:
        return 0
    return int(player_score)

@router.get("/game_pool", response_model=int)
async def get_game_pool():

    # 获取当前游戏的ID
    current_game_id = redis_client.get("CURRENT_GAME")
    if current_game_id is None:
        raise HTTPException(status_code=404, detail="No current game found.")
    current_game_id = current_game_id.decode('utf-8')

    # 获取奖池总金额
    pool_key = f"{current_game_id}_POOL"
    pool_amount = redis_client.get(pool_key)
    if pool_amount is None:
        return 0
    return int(pool_amount)

@router.get("/dealer_hand", response_model=str)
async def get_dealer_hand():
    # redis_client = RedisConnection.get_instance().client

    # 获取当前游戏的ID
    current_game_id = redis_client.get("CURRENT_GAME")
    if current_game_id is None:
        raise HTTPException(status_code=404, detail="No current game found.")
    current_game_id = current_game_id.decode('utf-8')

    # 获取荷官的手牌
    dealer_key = f"{current_game_id}_DEALER"
    dealer_hand = redis_client.get(dealer_key)
    if dealer_hand is None:
        raise HTTPException(status_code=404, detail="Dealer's hand not found.")
    return dealer_hand.decode('utf-8')

@router.get("/player/{player_name}/hand", response_model=str)
async def get_player_hand(player_name: str):

    # 获取当前游戏的ID
    current_game_id = redis_client.get("CURRENT_GAME")
    if current_game_id is None:
        raise HTTPException(status_code=404, detail="No current game found.")
    current_game_id = current_game_id.decode('utf-8')

    # 获取玩家当前游戏中的手牌
    hands_key = f"{current_game_id}_HANDS"
    player_hand = redis_client.hget(hands_key, player_name)
    if player_hand is None:
        raise HTTPException(status_code=404, detail="Player not found in the current game.")
    return player_hand.decode('utf-8')
@router.get("/current_game")
async def get_current_game():
    if not current_game:
        raise HTTPException(status_code=404, detail="No active game found")
    
    with current_game_lock:
        serialized_game = serialize_objectid(current_game)
        return JSONResponse(content=serialized_game)
    
@router.get("/player/{player_name}")
async def get_player_data(player_name: str):
    player_data = db.players.find_one({"name": player_name})
    if not player_data:
        raise HTTPException(status_code=404, detail="Player not found")
    
    serialized_player = serialize_objectid(player_data)
    return JSONResponse(content=serialized_player)

@router.get("/check_player_in_game/{player_name}")
async def check_player_in_game(player_name: str):
    if not current_game:
        raise HTTPException(status_code=404, detail="No active game found")
    
    player = current_game["players_dict"].get(player_name)
    if player:
        return JSONResponse(content={"hand": player["hand"]})
    else:
        return JSONResponse(content=-1)
    
    # Game Infos
@router.get("/game_info", response_model=CurrentGameInfo)
async def get_game_info():
    # redis_client = RedisConnection.get_instance().client

    # 获取当前游戏的ID
    current_game_id = redis_client.get("CURRENT_GAME")
    if current_game_id is None:
        raise HTTPException(status_code=404, detail="No current game found.")
    current_game_id = current_game_id.decode('utf-8')

    # 解析 game_id 获取游戏开始时间
    try:
        start_time = datetime.strptime(current_game_id, '%Y%m%d%H%M%S%f')
    except ValueError:
        raise HTTPException(status_code=500, detail="Invalid game ID format.")

    # 计算当前游戏时间
    current_time = datetime.utcnow()
    game_time = current_time - start_time

    # 获取奖池总金额
    pool_key = f"{current_game_id}_POOL"
    pool_amount = redis_client.get(pool_key)
    if pool_amount is None:
        pool_amount = 0
    else:
        pool_amount = int(pool_amount)

    # 获取玩家数量
    player_amount = redis_client.get(player_amount)
    if player_amount is None:
        player_amount = 0
    else:
        player_amount = int(player_amount)

    # 构造返回的JSON数据
    # 构造返回的JSON数据
    game_info = CurrentGameInfo(
        game_id=current_game_id,
        pool_amount=pool_amount,
        player_amount=player_amount,
        game_time=str(game_time)
    )

@router.websocket("/ws/game_info")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()

    try:
        while True:
            # 获取当前游戏的ID
            current_game_id = redis_client.get("CURRENT_GAME")
            if current_game_id is None:
                raise HTTPException(status_code=404, detail="No current game found.")
            current_game_id = current_game_id.decode('utf-8')

            # 解析 game_id 获取游戏开始时间
            try:
                start_time = datetime.strptime(current_game_id, '%Y%m%d%H%M%S%f')
            except ValueError:
                raise HTTPException(status_code=500, detail="Invalid game ID format.")

            # 计算当前游戏时间
            current_time = datetime.utcnow()
            game_time = current_time - start_time

            # 获取奖池总金额
            pool_key = f"{current_game_id}_POOL"
            pool_amount = redis_client.get(pool_key)
            if pool_amount is None:
                pool_amount = 0
            else:
                pool_amount = int(pool_amount)

            # 获取玩家数量
            player_amount_key = f"{current_game_id}_PLAYER_AMOUNT"
            player_amount = redis_client.get(player_amount_key)
            if player_amount is None:
                player_amount = 0
            else:
                player_amount = int(player_amount)

            # 构造返回的JSON数据
            game_info = CurrentGameInfo(
                game_id=current_game_id,
                pool_amount=pool_amount,
                player_amount=player_amount,
                game_time=str(game_time)
            )

            await websocket.send_json(game_info.dict())
            await asyncio.sleep(1)

    except WebSocketDisconnect:
        print("WebSocket connection closed")
    except Exception as e:
        print(f"An error occurred: {e}")
        await websocket.close()

    return game_info
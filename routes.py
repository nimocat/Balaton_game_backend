import json
from models import *
from game_logic import *
from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from database import db, serialize_objectid
from database import redis_client
from datetime import datetime

router = APIRouter()

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
    
@router.get("/player/{player_name}")
async def get_player_data(player_name: str):
    player_data = db.players.find_one({"name": player_name})
    if not player_data:
        raise HTTPException(status_code=404, detail="Player not found")
    
    serialized_player = serialize_objectid(player_data)
    return JSONResponse(content=serialized_player)

@router.get("/check_player_in_game/{player_name}")
async def check_player_in_game(player_name: str):
    current_game_id = redis_client.get("CURRENT_GAME")

    if not current_game_id:
        raise HTTPException(status_code=404, detail="No active game found")
    
    current_game_id = current_game_id.decode('utf-8')
    hands_key = f"{current_game_id}_HANDS"
    
    player_hand = redis_client.hget(hands_key, player_name)
    if player_hand:
        return JSONResponse(content={"hand": json.loads(player_hand.decode('utf-8'))})
    else:
        return JSONResponse(content=-1)

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

@router.post("/get_endgame_info", response_model=GameInfoResponse)
async def get_endgame_info(request: GameInfoRequest):
    game_id = request.game_id
    player_name = request.player_name

    # 获取荷官手牌
    dealer_key = f"{game_id}_DEALER"
    dealer_hand = redis_client.get(dealer_key)
    if not dealer_hand:
        raise HTTPException(status_code=404, detail="Game ID not found or dealer hand not set")
    dealer_hand = dealer_hand.decode('utf-8').split(' ')

    # 获取玩家手牌
    hands_key = f"{game_id}_HANDS"
    player_hand = redis_client.hget(hands_key, player_name)
    if not player_hand:
        raise HTTPException(status_code=404, detail="Player not found in the specified game")
    player_hand = json.loads(player_hand.decode('utf-8'))

    # 获取玩家最佳手牌和得分
    scores_key = f"{game_id}_SCORES"
    player_score = redis_client.zscore(scores_key, player_name)
    if player_score is None:
        raise HTTPException(status_code=404, detail="Player score not found")
    
    # 获取玩家奖励
    rewards_key = f"{game_id}_REWARDS"
    player_reward = redis_client.zscore(rewards_key, player_name)
    if player_reward is None:
        player_reward = 0  # If no reward found, default to 0

    # 获取玩家排名
    player_rank = redis_client.zrevrank(scores_key, player_name)
    if player_rank is None:
        raise HTTPException(status_code=404, detail="Player rank not found")

    # 获取奖池总金额
    pool_key = f"{game_id}_POOL"
    pool_amount = redis_client.get(pool_key)
    if pool_amount is None:
        pool_amount = 0
    else:
        pool_amount = int(pool_amount)

    # 获取所有玩家人数
    player_count = redis_client.get(f"{game_id}_COUNT")
    if player_count is None:
        player_count = 0
    else:
        player_count = int(player_count)

    # 构造返回的JSON数据
    game_info = GameInfoResponse(
        game_id=game_id,
        dealer_hand=dealer_hand,
        player_hand=player_hand,
        player_best_hand=player_hand,  # Assuming best hand is the player's hand itself
        player_score=player_score,
        player_reward=player_reward,
        player_rank=player_rank,
        pool_amount=pool_amount,
        player_count=player_count
    )

    return JSONResponse(content=game_info)

@router.post("/user_login")
async def user_login(request: LoginRequest):
    player_name = request.player_name
    return JSONResponse(content=load_player_items(player_name))

@router.post("/player_entrance")
async def player_entrance_route(request: EntranceRequest):
    player_name = request.player_name
    payment = request.payment

    if payment == 20:
        card_num = 2
    elif payment == 40:
        card_num = 3
    else:
        raise HTTPException(status_code=400, detail="Invalid payment amount")

    player_entrance(player_name, card_num)
    return {"message": f"Player {player_name} entered the game with {card_num} cards."}
import json
from models import *
from game_logic import *
from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from database import db, serialize_objectid
from database import redis_client
from datetime import datetime

router = APIRouter()

@router.get("/game_id", response_model=str, summary='Get the current game id', tags=['Info'])
async def get_current_game_id():

    # 获取当前游戏的ID
    current_game_id = redis_client.get("CURRENT_GAME")
    if current_game_id is None:
        raise HTTPException(status_code=404, detail="No current game found.")
    return current_game_id.decode('utf-8')

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
    

@router.get("/check_player_in_game/{player_name}", summary='Check if the player is in current game', tags=['Player'])
async def check_player_in_game(player_name: str):
    current_game_id = redis_client.get("CURRENT_GAME")

    if not current_game_id:
        raise HTTPException(status_code=404, detail="No active game found")
    
    current_game_id = current_game_id.decode('utf-8')
    hands_key = f"{current_game_id}_HANDS"

    player_hand = redis_client.hget(hands_key, player_name)
    if player_hand:
        return JSONResponse(content={"cards": player_hand.decode('utf-8'), "status": 1})
    else:
        return JSONResponse(content={"status": 0})

@router.get("/info/top_daily_rewards", response_model=TopDailyRewardsResponse, summary="Get top daily rewards", tags=["Info"])
async def get_top_daily_rewards():
    """
    Retrieve the top 100 players with the highest rewards for the day from the REWARD_RANKING_DAY sorted set.
    """
    # 获取 REWARD_RANKING_DAY 中前 100 名玩家
    top_players = redis_client.zrevrange("REWARD_RANKING_DAY", 0, 99, withscores=True)

    # 构造响应数据
    top_players_data = [
        {"player_name": player.decode('utf-8'), "reward": reward}
        for player, reward in top_players
    ]

    return {"top_players": top_players_data}

@router.get("/info/game_items", response_model=GameItemsResponse, summary="Get all game items", tags=["Info"])
async def get_game_items():
    """
    Retrieve all game items stored in Redis.
    """
    keys = redis_client.keys("game_item:*")
    items = []
    
    for key in keys:
        item_data = redis_client.hgetall(key)
        item = GameItem(
            item_id=int(key.decode('utf-8').split(":")[1]),
            type=int(item_data[b'type'].decode('utf-8')),
            name=item_data[b'name'].decode('utf-8'),
            short_description=item_data[b'short_description'].decode('utf-8'),
            long_description=item_data[b'long_description'].decode('utf-8'),
            available=bool(int(item_data[b'available'].decode('utf-8')))
        )
        items.append(item)
    
    return {"items": items}

@router.get("/info/shop_items", response_model=ShopItemsResponse, summary="Get all shop items", tags=["Info"])
async def get_shop_items():
    """
    Retrieve all shop items stored in Redis.
    """
    keys = redis_client.keys("shop_item:*")
    items = []

    for key in keys:
        item_data = redis_client.hgetall(key)
        item = ShopItem(
            item_id=int(key.decode('utf-8').split(":")[1]),
            price=int(item_data[b'price'].decode('utf-8')),
            avaliable=bool(int(item_data[b'avaliable'].decode('utf-8'))),
            discount=float(item_data[b'discount'].decode('utf-8')),
            num=int(item_data[b'num'].decode('utf-8'))
        )
        items.append(item)

    return {"items": items}

@router.get("/game_info", response_model=CurrentGameInfo, summary='Get the running game information', tags=['Info'])
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
    game_seconds = game_time.total_seconds()  # 计算游戏已经进行了多少秒
    game_showtime = int(30 - game_seconds)
    # 获取奖池总金额
    pool_key = f"{current_game_id}_POOL"
    pool_amount = redis_client.get(pool_key)
    if pool_amount is None:
        pool_amount = 0
    else:
        pool_amount = int(pool_amount)

    # 获取玩家数量
    player_count_key = f"{current_game_id}_POOL"
    player_amount = redis_client.get(player_count_key)
    if player_amount is None:
        player_amount = 0
    else:
        player_amount = int(player_amount)

    game_info = CurrentGameInfo(
        game_id=current_game_id,
        pool_amount=pool_amount,
        player_amount=player_amount,
        game_time=game_showtime  # 返回游戏已经进行的秒数
    )
    
    return JSONResponse(content=game_info.dict())

@router.post("/get_endgame_info", response_model=GameInfoResponse, summary='Get the ended game information', tags=['Info'])
async def get_endgame_info(request: GameInfoRequest):
    game_id = request.game_id
    player_name = request.player_name

    # 获取荷官手牌
    dealer_key = f"{game_id}_DEALER"
    dealer_hand = redis_client.get(dealer_key)
    if not dealer_hand:
        raise HTTPException(status_code=404, detail="Game ID not found or dealer hand not set")
    dealer_hand = dealer_hand.decode('utf-8')
    print(dealer_hand)

    # 获取玩家手牌
    hands_key = f"{game_id}_HANDS"
    player_hand = redis_client.hget(hands_key, player_name)
    if not player_hand:
        raise HTTPException(status_code=404, detail="Player not found in the specified game")
    player_hand = player_hand.decode('utf-8')

    # 获取玩家最佳手牌和得分
    scores_key = f"{game_id}_SCORES"
    player_score = redis_client.zscore(scores_key, player_name)
    if player_score is None:
        raise HTTPException(status_code=404, detail="Player score not found")
    
    # 获取玩家手牌
    best_hands_key = f"{game_id}_BEST_HANDS"
    player_best_hand = redis_client.hget(best_hands_key, player_name)
    if not player_hand:
        raise HTTPException(status_code=404, detail="Player not found in the specified game")
    player_best_hand = player_best_hand.decode('utf-8')

    # 获取玩家奖励
    rewards_key = f"{game_id}_REWARDS"
    player_reward = int(redis_client.zscore(rewards_key, player_name))
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
        player_best_hand=player_best_hand,  # Assuming best hand is the player's hand itself
        player_score=player_score,
        player_reward=player_reward,
        player_rank=player_rank,
        pool_amount=pool_amount,
        player_count=player_count
    )

    return JSONResponse(content=game_info.dict())

# Player routers
@router.post("/user_login", summary='Invoke once player is login', tags=['Player'])
async def user_login(request: LoginRequest):
    player_name = request.player_name
    return JSONResponse(content=load_player_items(player_name))

@router.post("/player_entrance", summary='Invoke once player is entering the game', tags=['Player'])
async def player_entrance_route(request: EntranceRequest):
    player_name = request.player_name
    payment = request.payment

    if payment == 20:
        card_num = 2
    elif payment == 40:
        card_num = 3
    else:
        raise HTTPException(status_code=400, detail="Invalid payment amount")

    cards = player_entrance(player_name, card_num)
    return {"message": f"Player {player_name} entered the game with {card_num} cards.", "cards": cards} # 返回手牌

@router.get("/players/{player_name}/items",response_model=PlayerItemsResponse, summary='Get the player items', tags=['Player'])
async def get_player_items(player_name: str):
    # 获取玩家 items
    player_items_key = f"{player_name}_ITEMS"
    player_items = redis_client.hgetall(player_items_key)
    
    if not player_items:
        raise HTTPException(status_code=404, detail="Player items not found")

    # 转换 Redis 数据为 Python 字典，并将字节转换为字符串
    player_items = {key.decode('utf-8'): value.decode('utf-8') for key, value in player_items.items()}

    return {"player_name": player_name, "items": player_items}

@router.get("/players/{player_name}/history", response_model=PlayerHistoryResponse, summary="Get player history", description="Retrieve the game history for a given player.", tags=['Player'])
async def get_player_history(player_name: str):
    """
    Retrieve the game history for a given player.
    - **player_name**: The name of the player.
    """
    player = db.players.find_one({"name": player_name})
    if not player:
        raise HTTPException(status_code=404, detail="Player not found")

    history = player.get("history", [])
    formatted_history = []
    
    for entry in history:
        game_id = entry['game_id']
        hand = entry['hand']
        score = entry['score']
        reward = entry['reward']
        
        # Determine bet based on the number of items in hand
        hand_list = eval(hand)
        if len(hand_list) == 3:
            bet = 40
        elif len(hand_list) == 2:
            bet = 20
        else:
            bet = 0
        
        # Format game_id to "YYYY/MM/DD HH:MM"
        formatted_game_id = f"{game_id[:4]}/{game_id[4:6]}/{game_id[6:8]} {game_id[8:10]}:{game_id[10:12]}"
        
        formatted_history.append({
            "game_id": formatted_game_id,
            "hand": hand,
            "bet": bet,
            "score": score,
            "reward": reward
        })

    return {"player_name": player_name, "history": formatted_history}
 # Tasks
@router.post("/tasks/invite", summary='Invoke when invite link has been clicked', tags=['Task'])
async def invite_new_user(request: InviteRequest):
    inviter = request.inviter
    invitee = request.invitee
    
    invitee_collection = db.players
    existing_invitee = invitee_collection.find_one({"name": invitee})
    existing_invitee_in_redis = redis_client.hgetall(f"{invitee}_ITEMS")

    if existing_invitee or existing_invitee_in_redis:
        return {"message": "Invitee already exists in the database", "status": 0}

    # 如果 invitee 是新用户，则 inviter 获得 80 tokens，invitee 获得 100 tokens
    redis_client.incrby(f"{inviter}_TOKENS", 80)
    redis_client.incrby(f"{invitee}_TOKENS", 100)

    # 将 Redis 数据持久化到 MongoDB 中
    update_player_items_to_mongo(inviter)
    update_player_items_to_mongo(invitee)

    return {"message": f"Inviter {inviter} received 80 tokens. New invitee {invitee} received 100 tokens.", "status": 1}

@router.get("/tasks/share_to_group", summary='Invoke once share to group button is clicked', tags=['Task'])
async def share_to_group(sharer: str):
    
    # 查找玩家
    player = db.players.find_one({"name": sharer})
    if not player:
        raise HTTPException(status_code=404, detail="Player not found")

    # 查找任务ID
    task = db.tasks.find_one({"name": "Daily Share Task"})
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    task_id = str(task['task_id'])
    
    # 检查玩家的任务完成情况
    player_task_record = next((task for task in player.get("tasks", []) if task["task_id"] == task_id), None)
    
    if player_task_record:
        can_complete, remain_time = check_task_completion(player_task_record, 24)
        if not can_complete:
            return {"message": f"You have already completed this task today. Time remaining: {remain_time}"}

        # 更新任务完成时间
        player_task_record["last_completed"] = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
    else:
        # 添加新任务记录
        player_task_record = {
            "task_id": task_id,
            "last_completed": datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S'),
            "completed_count": 1
        }
        player.setdefault("tasks", []).append(player_task_record)

    # 增加 60 个代币
    redis_client.incrby(f"{sharer}_TOKENS", 60)

    # 将 Redis 数据持久化到 MongoDB 中
    persist_player_items_to_mongo(sharer)

    return {"message": f"Sharer {sharer} received 60 tokens for sharing to a group."}

@router.get("/tasks/all_task", summary='Get the task list of a single player', tags=['Task'])
async def get_tasks(player_name: str):
    # 从 MongoDB 中获取任务列表 task_list，并为 task_list 新加一列 remain_time（默认为 0）和 available 字段（默认为 1）
    task_list = list(db.tasks.find({}))
    for task in task_list:
        task['remain_time'] = 0
        task['available'] = 1

    # 获取 db.players.{player_name}.tasks 的任务完成记录表
    player = db.tasks.find_one({"name": player_name})
    if not player:
        raise HTTPException(status_code=404, detail="Player not found")

    player_tasks = {str(task_record["task_id"]): task_record for task_record in player.get("tasks", [])}

    # 判断所有 tasks 是否到了刷新时间，如果还没有，则在 task_list 中给 available 修改为 0，并填写 remain_time
    for task in task_list:
        task_id_str = str(task['task_id'])
        if task_id_str in player_tasks:
            last_completed = player_tasks[task_id_str].get("last_completed")
            if last_completed:
                last_completed = datetime.strptime(last_completed, '%Y-%m-%d %H:%M:%S')
                refresh_time = timedelta(hours=task['refresh_time'])
                time_diff = datetime.utcnow() - last_completed
                if time_diff < refresh_time:
                    task['available'] = 0  # 任务不可以继续做
                    task['remain_time'] = str(refresh_time - time_diff)

    return {"tasks": task_list}
import json
from models import *
from game_logic import *
from fastapi import APIRouter, HTTPException, Path
from fastapi.responses import JSONResponse
from database import db
from database import redis_client
from datetime import datetime
from hooks import player_hook
from fastapi import Request, Depends
import hmac
import hashlib

ACCESS_TOKEN = "6970070520:AAE_0lMuJNo9Uyh9O1xZQ0LeVMBFjl3bXPE"

async def verify_balaton_access_token(request: Request):
    token = request.headers.get("Balaton-Access-Token")
    if not token:
        raise HTTPException(status_code=401, detail="Balaton-Access-Token is missing")

    data = prepare_data_to_check(token)
    username = data.get('username')
    hash_value = data.get('hash')

    if not username or not hash_value:
        raise HTTPException(status_code=400, detail="Username or hash is missing")

    redis_key = f"{username}_HASH"
    stored_hash = redis_client.get(redis_key)

    if stored_hash and stored_hash.decode('utf-8') == hash_value:
        return True
    else:
        if check_hash(data, ACCESS_TOKEN):
            redis_client.setex(redis_key, 2 * 60 * 60, hash_value)  # Set expiry to 2 hours
            return True
        else:
            raise HTTPException(status_code=401, detail="Invalid hash")

def prepare_data_to_check(init_data: str) -> dict:
    return dict(item.split('=') for item in init_data.split('&'))

def check_hash(init_data: str, tg_token: str) -> bool:
    data_to_check = prepare_data_to_check(init_data)
    received_hash = data_to_check.get('hash')
    secret_key = hmac.new(tg_token.encode(), "WebAppData".encode(), digestmod=hashlib.sha256).digest()
    data_check_string = '\n'.join(f"{key}={value}" for key, value in sorted(data_to_check.items())).encode()
    hash_check = hmac.new(secret_key, data_check_string, digestmod=hashlib.sha256).hexdigest()
    return hash_check == received_hash

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

@router.get("/player/{player_name}/hand", response_model=str, dependencies=[Depends(verify_balaton_access_token)])
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
    

@router.get("/check_player_in_game/{player_name}", summary='Check if the player is in current game', tags=['Player'], dependencies=[Depends(verify_balaton_access_token)])
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

    # 计算当前游戏时间
    game_showtime = redis_client.ttl("CURRENT_GAME")
    if game_showtime == -2:
        raise HTTPException(status_code=404, detail="No current game found.")
    
    # 获取奖池总金额
    pool_key = f"{current_game_id}_POOL"
    pool_amount = redis_client.get(pool_key)
    if pool_amount is None:
        pool_amount = 0
    else:
        pool_amount = int(pool_amount)

    # 获取玩家数量
    player_count_key = f"{current_game_id}_COUNT"
    player_amount = redis_client.get(player_count_key)
    if player_amount is None:
        player_amount = 0
    else:
        player_amount = int(player_amount)

    game_info = CurrentGameInfo(
        game_id=current_game_id, # 当前游戏ID
        pool_amount=pool_amount, # 奖池大小
        player_amount=player_amount, # 玩家总数
        game_time=game_showtime  # 返回游戏已经进行的秒数
    )
    
    return JSONResponse(content=game_info.dict())

@router.post("/get_endgame_info", response_model=GameInfoResponse, summary='Get the ended game information', tags=['Info'], dependencies=[Depends(verify_balaton_access_token)])
async def get_endgame_info(request: GameInfoRequest):
    game_id = request.game_id if request.game_id else redis_client.get("LAST_GAME").decode('utf-8')
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
@router.post("/user_login", summary='Invoke once player is login', tags=['Player'], dependencies=[Depends(verify_balaton_access_token)])
async def user_login(request: LoginRequest):
    player_name = request.player_name
    # Update the player's last login time in MongoDB
    player_hook.login_hook(player_name)
    
    return JSONResponse(content=load_player_tokens(player_name))

# Player routers
@router.post("/daily_checkin", summary='Invoke once player click on checkin button', tags=['Player'])
async def daily_checkin(request: LoginRequest):
    player_name = request.player_name
    player_data = db.players.find_one({"name": player_name})
    if not player_data:
        raise Exception("Player not found")

    today = datetime.utcnow().date()
    last_checkin_date = player_data.get('last_checkin_date')
    
    if last_checkin_date:
        last_checkin_date = datetime.strptime(last_checkin_date, '%Y-%m-%d').date()
        
        if last_checkin_date == today:
            # 如果上次签到是今天，返回已经签到的信息
            return {"message": "Already checked in today."}
        elif last_checkin_date == today - timedelta(days=1):
            new_consecutive_checkins = player_data.get('consecutive_checkins', 0) + 1
        else:
            new_consecutive_checkins = 1
    else:
        new_consecutive_checkins = 1
    
    # update可以claim的checkin任务
    update_can_claim_tasks(player_name=player_name, task_type=2)
    # Retrieve check-in rewards based on the type '1' and the number of consecutive check-ins
    # 结算当前checkin的奖励(task_type为1，结算类型为0，立刻结算)
    settle_rewards(player_name=player_name, checkpoint=new_consecutive_checkins, task_type=1)

    # Update MongoDB
    db.players.update_one(
        {"name": player_name},
        {"$set": {
            "last_checkin_date": today.strftime('%Y-%m-%d'),
            "consecutive_checkins": new_consecutive_checkins
        }}
    )

    update_player(player_name=player_name)
    return {"message": "Check-in successful", "consecutive_days": new_consecutive_checkins}

@router.get("/player/{player_name}/consecutive_checkins", summary='Return a int to identify the consecutive_checkins', response_model=int, tags=["Player"], dependencies=[Depends(verify_balaton_access_token)])
async def get_consecutive_checkins(player_name: str):
    """
    Retrieve the number of consecutive check-in days for a given player.
    If no record is found, returns 0.
    """
    player_data = db.players.find_one({"name": player_name}, {"consecutive_checkins": 1})
    
    if not player_data:
        return 0  # No record found, return 0
    
    return player_data.get('consecutive_checkins', 0)

@router.post("/player_entrance", summary='Invoke once player is entering the game', tags=['Player'], dependencies=[Depends(verify_balaton_access_token)])
async def player_entrance_route(request: EntranceRequest):
    player_name = request.player_name
    payment = request.payment

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

    cards = player_entrance(player_name, card_num)
    return {"message": f"Player {player_name} entered the game with {card_num} cards.", "cards": cards} # 返回手牌

@router.get("/player/{player_name}/tokens", response_model=float, summary='Get the player tokens', tags=['Player'], dependencies=[Depends(verify_balaton_access_token)])
async def get_player_tokens(player_name: str):
    """
    Retrieve the number of tokens for a given player from Redis.
    """
    player_tokens_key = f"{player_name}_TOKENS"
    tokens = redis_client.get(player_tokens_key)
    
    if tokens is None:
        raise HTTPException(status_code=404, detail="Player tokens not found")
    
    return float(tokens)

@router.get("/players/{player_name}/items",response_model=PlayerItemsResponse, summary='Get the player items', tags=['Player'], dependencies=[Depends(verify_balaton_access_token)])
async def get_player_items(player_name: str):
    # 获取玩家 items
    player_items_key = f"{player_name}_ITEMS"
    player_items = redis_client.hgetall(player_items_key)
    
    if not player_items:
        raise HTTPException(status_code=404, detail="Player items not found")

    # 转换 Redis 数据为 Python 字典，并将字节转换为字符串
    player_items = {key.decode('utf-8'): value.decode('utf-8') for key, value in player_items.items()}

    return {"player_name": player_name, "items": player_items}

@router.get("/players/{player_name}/history", response_model=PlayerHistoryResponse, summary="Get player history", description="Retrieve the game history for a given player.", tags=['Player'], dependencies=[Depends(verify_balaton_access_token)])
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
 # 客户端判断，如果initData里面有start_param，代表是邀请进入的，走邀请login，否则走user_login
@router.post("/invite_login", summary='Invoke when invite link has been clicked', tags=['Player'], dependencies=[Depends(verify_balaton_access_token)])
async def invite_new_user(request: InviteRequest):
    inviter = request.inviter # start_param带的
    invitee = request.invitee # username带的
    player_hook.login_hook(invitee)

    INVITEE_REWARD = 100
    INVITER_REWARD = 80

    invitee_collection = db.players
    existing_invitee = invitee_collection.find_one({"name": invitee})

    if existing_invitee:
        return {"message": "Invitee already exists in the database", "status_code": 404}

    inviter_data = invitee_collection.find_one({"name": inviter})
    if inviter_data:
        referrals = inviter_data.get("referrals", [])
        if len(referrals) >= 10:
            return {"status_code": 404, "message": "Inviter has reached the maximum number of referrals"}

    # 如果 invitee 是新用户，则 inviter 获得 80 tokens，invitee 获得 100 tokens
    redis_client.incrby(f"{inviter}_TOKENS", INVITER_REWARD)
    redis_client.incrby(f"{invitee}_TOKENS", INVITEE_REWARD)

    # 处理邀请人的父节点，和邀请人的祖父节点
    # Retrieve the inviter's inviter (grand-inviter) from the database
    inviter_data = invitee_collection.find_one({"name": inviter})
    if inviter_data and "inviter" in inviter_data:
        grand_inviter = inviter_data["inviter"]
        # Calculate rewards for inviter's inviter (grand-inviter)
        grand_inviter_reward = INVITER_REWARD * 0.1
        
        # Check if grand_inviter's tokens exist in Redis, if not load from MongoDB
        grand_inviter_tokens_key = f"{grand_inviter}_TOKENS"
        if not redis_client.exists(grand_inviter_tokens_key):
            load_player_tokens_to_redis(grand_inviter)
        redis_client.incrbyfloat(grand_inviter_tokens_key, float(grand_inviter_reward))

        # Retrieve the grand-inviter's inviter (great-grand-inviter) from the database
        grand_inviter_data = invitee_collection.find_one({"name": grand_inviter})
        if grand_inviter_data and "inviter" in grand_inviter_data:
            great_grand_inviter = grand_inviter_data["inviter"]
            # Calculate rewards for grand-inviter's inviter (great-grand-inviter)
            great_grand_inviter_reward = INVITER_REWARD * 0.025
            
            # Check if great_grand_inviter's tokens exist in Redis, if not load from MongoDB
            great_grand_inviter_tokens_key = f"{great_grand_inviter}_TOKENS"
            if not redis_client.exists(great_grand_inviter_tokens_key):
                load_player_tokens_to_redis(great_grand_inviter)
            redis_client.incrbyfloat(great_grand_inviter_tokens_key, float(great_grand_inviter_reward))

    # Set the inviter field for the invitee in MongoDB
    invitee_collection.update_one(
        {"name": invitee},
        {"$set": {"inviter": inviter}},
        upsert=True
    )

    # Add the invitee to the inviter's referrals list in MongoDB
    invitee_collection.update_one(
        {"name": inviter},
        {"$push": {"referrals": invitee}},
        upsert=True
    )

    # 将 Redis 数据持久化到 MongoDB 中
    update_player_tokens_to_mongo(inviter)
    update_player_tokens_to_mongo(invitee)

    return {"message": f"Inviter {inviter} received 80 tokens. New invitee {invitee} received 100 tokens.", "status": 1}

# can_claim也代表着完成了任务
@router.get("/tasks/{player_name}/can_claim_tasks", response_model=list, summary="Get list of can claim task IDs for a player", tags = ['Task'])
async def get_can_claim_tasks(player_name: str):
    """
    Retrieve a list of task IDs that the player can claim.
    """
    try:
        return fetch_claim_tasks(player_name=player_name)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
@router.post("/tasks/{player_name}/claim/{task_id}", summary="Claim a checkin task reward", tags = ['Task'])
async def claim_task(player_name: str, task_id: str = Path(..., description="The ID of the task to claim")):
    """
    Claim a checkin task reward if the task_id is in the player's CANCLAIM set.
    """
    # Check if the task_id is in the CANCLAIM set
    can_claim_tasks = fetch_claim_tasks(player_name)
    if task_id.encode('utf-8') not in can_claim_tasks:
        raise HTTPException(status_code=404, detail="Task ID not claimable or already claimed")

    # Retrieve the task's rewards directly using the task_id from Redis
    task_rewards = redis_client.hget(f"task:{task_id}", "rewards")
    if not task_rewards:
        raise HTTPException(status_code=404, detail="Task rewards not found for given task ID")
    # Decode and evaluate the rewards string to convert it into a dictionary
    rewards = eval(task_rewards.decode('utf-8'))

    # Use Redis transaction to ensure atomicity
    send_rewards(player_name=player_name, rewards=rewards, task_id=task_id)

    # Update MongoDB with the new items (synchronize Redis to MongoDB)
    update_player(player_name=player_name)
    return {"message": "Task claimed successfully", "rewards": rewards}

@router.get("/tasks/{player_name}/checkin_claim_list", response_model=Type2TaskResponse, summary="Get all type 2 tasks in CANCLAIM and CLAIMED", tags=['Task'])
async def get_type2_tasks(player_name: str):
    """
    Retrieve all type 2 task IDs in CANCLAIM and CLAIMED sets for a given player.
    """
    try:
        type2_can_claim = fetch_claim_tasks(player_name, task_type=2)
        type2_claimed = fetch_claim_tasks(player_name, task_type=2, claim_type="CLAIMED")
        
        return {
            "can_claim": type2_can_claim,
            "claimed": type2_claimed
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/tasks/farming", response_model=FarmingResponse, summary="Handle farming tasks for a player", tags=['Task'])
async def handle_farming_task(request: LoginRequest):
    """
    Creates or updates a farming task for a player, setting rewards with an expiration.
    """
    player_name = request.player_name
    farming_key = f"{player_name}_FARMING"
    task_id = "2001"
    
    # Check if the key already exists
    existing_rewards = redis_client.get(farming_key)
    if existing_rewards:
        # Calculate the rewards gained so far and the rate of increase per second
        elapsed_time = redis_client.ttl(farming_key)
        total_time = 4 * 3600  # 4 hours in seconds
        remaining_time = total_time - elapsed_time
        rewards_per_second = eval(existing_rewards.decode('utf-8')) / total_time
        accumulated_rewards = rewards_per_second * elapsed_time
        
        return FarmingResponse(
            status="1",
            accumulated_rewards=accumulated_rewards,
            rewards_per_second=rewards_per_second,
            remaining_time=remaining_time
        )
    else:
        # Retrieve the rewards for task_id 2001
        task_rewards = redis_client.hget(f"task:{task_id}", "rewards")
        if not task_rewards:
            raise HTTPException(status_code=404, detail="Task rewards not found for given task ID")
        
        # Set the rewards in Redis with an expiration of 4 hours
        redis_client.setex(farming_key, 14400, task_rewards)  # 14400 seconds = 4 hours
        
        return FarmingResponse(
            status="1",
            message="Farming task initiated successfully."
        )
    
@router.get("/tasks/farming/status", response_model=FarmingResponse, summary="Get the status of a farming task for a player", tags=['Task'])
async def get_farming_task_status(request: LoginRequest):
    """
    Retrieves the status of a farming task for a player. If the task has started, returns all information.
    If not started, returns status as 0.
    If already started, returns status as 1.
    If can claim, returns status as 2.
    """
    player_name = request.player_name
    farming_key = f"{player_name}_FARMING"
    
    # Check if the key exists to determine if the task has started
    existing_rewards = redis_client.get(farming_key)
    if existing_rewards:
        # Calculate the rewards gained so far and the rate of increase per second
        elapsed_time = redis_client.ttl(farming_key)
        total_time = 4 * 3600  # 4 hours in seconds
        remaining_time = total_time - elapsed_time
        rewards_per_second = eval(existing_rewards.decode('utf-8')) / total_time
        accumulated_rewards = rewards_per_second * elapsed_time
        
        return FarmingResponse(
            status="1",
            accumulated_rewards=accumulated_rewards,
            rewards_per_second=rewards_per_second,
            remaining_time=remaining_time
        )
    else:
        can_claim_key = f"{player_name}_CANCLAIM"
        if redis_client.sismember(can_claim_key, 301):
            return FarmingResponse(status="2", message="Task can be claimed")
        else:
            return FarmingResponse(status="0", message="Task can start")

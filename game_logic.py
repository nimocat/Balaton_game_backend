import threading
import time
import random
import json
from typing import Dict, List, Optional
import redis
import math
import threading
import logging
import pandas as pd
from logging.handlers import RotatingFileHandler
from datetime import datetime, timedelta
from bson import ObjectId
from database import db, redis_client
from alg import generate_hand, calculate_score, combine_hands, dealer_draw, calculate_reward

# 配置日志记录
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
handler = RotatingFileHandler("balaton.log", maxBytes= 500 * 1024, backupCount= 3)
handler.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)

logger.addHandler(handler)
console = logging.StreamHandler()
console.setLevel(logging.INFO)

logger.addHandler(console)

# 游戏引擎单例
def start_new_game():

    CURRENT_GAME = "CURRENT_GAME"
    DURATION = 35

    # # 检查是否已存在游戏ID
    # if redis_client.get(CURRENT_GAME):
    #     return  # 如果CURRENT_GAME已存在，不执行任何操作

    # 生成game_id
    game_id = datetime.utcnow().strftime('%Y%m%d%H%M%S%f')

    redis_client.set(CURRENT_GAME, game_id)
    # 设置过期时间，如果查询不到CURRENT_GAME，则为游戏结算中，未开始新游戏。如果查询到的CURRENT_GAME和客户端存储的game_id不同，则说明已经开始一局新游戏
    redis_client.expire(CURRENT_GAME, DURATION)
    redis_client.publish("countdown_channel", f"Countdown started for {CURRENT_GAME} with duration {DURATION} seconds")

    logger.info(f"Game ID: {game_id} Generated, New Game Start")
    # 存入数据库，所有基于redis的新数据添加，都根据CURRENT_GAME这个值来进行

def player_to_dict(player, current_game):
    return {
        "name": player.name,
        "hand": player.hand,
        "score": 0,
        "reward": 0,
        "_id": ObjectId(),
        "game_id": current_game["game_id"],
        "game_ids": []
    }

def load_player_items(player_name: str) -> dict:
    player_items_key = f"{player_name}_ITEMS"

    # 尝试从 Redis 中获取玩家的 _ITEMS 信息
    player_items = redis_client.hgetall(player_items_key)
    if player_items:
        # 如果 Redis 中存在，返回该信息
        logger.info(f"Player {player_name}'s info is in Redis, fetch from Redis")

        player_items = {key.decode('utf-8'): value.decode('utf-8') for key, value in player_items.items()}
        return player_items
    
    # 如果 Redis 中不存在，从 MongoDB 中获取玩家的 items 信息
    logger.info(f"Player {player_name}'s info is not in Redis, fetch from Database")

    return load_player_to_redis(player_name)

def load_player_tokens(player_name: str) -> float:
    """
    Load the player's tokens from Redis. If not found, fetch from MongoDB and update Redis.
    
    Args:
    player_name (str): The name of the player whose tokens need to be fetched.
    
    Returns:
    int: The number of tokens the player has.
    """
    player_tokens_key = f"{player_name}_TOKENS"
    tokens = redis_client.get(player_tokens_key)
    
    if tokens is None:
        # Fetch from MongoDB if not found in Redis
        player_data = db.players.find_one({"name": player_name}, {"tokens": 1})
        if player_data and "tokens" in player_data:
            tokens = player_data["tokens"]
            # Update Redis with the fetched data
            redis_client.set(player_tokens_key, tokens)
            logger.info(f"Loaded {player_name}'s tokens from MongoDB and updated Redis: {tokens}")
        else:
            tokens = 0  # Default to 0 if not found in MongoDB either
            logger.info(f"No tokens found for {player_name} in MongoDB. Defaulting to 0.")
    
    return float(tokens)


def update_player_items_to_mongo(player_name: str):
    player_key = f"{player_name}_ITEMS"

    # Check if the player exists in Redis
    if not redis_client.exists(player_key):
        logger.error(f"Player {player_name} not found in Redis")
        raise ValueError(f"Player {player_name} not found in Redis")

    # Get player items from Redis
    player_items = redis_client.hgetall(player_key)

    # Convert Redis data to the appropriate format
    items = {str(key.decode('utf-8')): int(value.decode('utf-8')) for key, value in player_items.items()}
    # Update the player's items in MongoDB
    db.players.update_one(
        {"name": player_name},
        {"$set": {"items": items}},
        upsert=True  # This option creates the document if it doesn't exist
    )

    logger.info(f"Player {player_name}'s items updated in MongoDB")

def load_player_to_redis(player_name: str):
    # 从 MongoDB 中获取玩家信息
    player = db.players.find_one({"name": player_name})
    if not player:
        logger.info(f"Player {player_name} not found in MongoDB")
        return
    # 获取玩家的 items 字段
    player_items = player.get('items', {})

    # 如果 items 为空，记录日志并退出函数
    if not player_items:
        logger.info(f"Player {player_name} has no items to load into Redis")
        return

    # 将玩家信息存储在 Redis 中的哈希表中
    player_items_key = f"{player_name}_ITEMS"
    
    with redis_client.pipeline() as pipe:
        pipe.hmset(player_items_key, player_items)
        pipe.execute()
    
    logger.info(f"Player {player_name} loaded to Redis with items: {player_items}")
    return player_items

def load_player_tokens_to_redis(player_name: str) -> bool:
    # 从 MongoDB 中获取玩家的 tokens 信息
    player_data = db.players.find_one({"name": player_name}, {"tokens": 1})
    if not player_data:
        logger.info(f"Player {player_name} not found in MongoDB")
        return False

    if 'tokens' not in player_data:
        logger.info(f"Player {player_name} tokens not found in MongoDB")
        return True

    # 获取玩家的 tokens 数量
    player_tokens = player_data['tokens']

    # 将 tokens 信息存储在 Redis 中
    player_tokens_key = f"{player_name}_TOKENS"
    redis_client.set(player_tokens_key, player_tokens)

    logger.info(f"Player {player_name} tokens loaded to Redis: {player_tokens}")
    return True

# 每个player进入游戏时执行
def player_entrance(player_name, card_num):
    # logger
    logger.info(f"Player {player_name} entering game with {card_num} Pokers")

    # 随机card_num张玩家的手牌
    player_hand = generate_hand(card_num)
    hand_str = str(player_hand)  # 将手牌转换为字符串存储

    # 计算开销
    cost = 40 if card_num == 3 else 20

    # 获取当前游戏的ID
    current_game = redis_client.get("CURRENT_GAME")
    if not current_game:
        raise ValueError("No current game is running")

    current_game = current_game.decode('utf-8')

    # 检查玩家的 ITEMS 中的 token 数量是否足够
    player_items_key = f"{player_name}_ITEMS"
    player_tokens = f"{player_name}_TOKENS"

    # 创建一个 Redis 事务（Pipeline）
    with redis_client.pipeline() as pipe:
        while True:
            try:
                # Watch the keys that will be modified
                pipe.watch(f"{current_game}_HANDS", f"{current_game}_POOL", f"{player_name}_ITEMS", f"{current_game}_COUNT", player_tokens)

                # 开始事务
                pipe.multi()

                # 将玩家及其对应的手牌加入当前游戏的 HANDS hash table
                pipe.hset(f"{current_game}_HANDS", player_name, hand_str)

                # 将 POOL 的数字增加相应的 cost
                pipe.incrby(f"{current_game}_POOL", cost)

                # 注意，玩家需要在连接完钱包或者进入界面时，就把他的信息加载到redis中
                # 将玩家的 ITEMS 中的 token 数量减少相应的 cost
                tokens = redis_client.get(player_tokens)
                if tokens is None or float(tokens) < cost:
                    return {"error": "Insufficient tokens"}
                pipe.incrbyfloat(player_tokens, -cost)

                # 将当前游戏的 COUNT 增加1
                pipe.incr(f"{current_game}_COUNT")

                # 执行事务
                pipe.execute()
                break  # If execute is successful, exit the loop
            except redis.WatchError:
                # 如果在事务执行期间键的值发生了变化，重试
                continue
    logger.info(f"Player {player_name} finished enter game, data updated to Redis")
    return hand_str

    
# 模拟测试
def player_entry():
    global current_game
    while True:
        time.sleep(random.uniform(0.5, 2))  # 更快的随机等待时间，模拟玩家随机进入游戏

        with redis_client.pipeline() as pipe:
            while True:
                try:
                    # 获取CURRENT_GAME的ID
                    current_game_id = redis_client.get("CURRENT_GAME")
                    if not current_game_id:
                        raise ValueError("No current game is running")
                    current_game_id = current_game_id.decode('utf-8')

                    # 监视将被修改的键
                    pipe.watch(f"{current_game_id}_COUNT, {current_game_id}_HANDS", f"{current_game_id}_POOL")
                    
                    # 获取当前玩家数
                    current_count = int(redis_client.get(f"{current_game_id}_COUNT") or 0)
                    player_name = f"Player{current_count + 1}"
                    player_hand = generate_hand(2)  # 假设每个玩家有3张牌
                    hand_str = json.dumps(player_hand)  # 将手牌转换为字符串存储
                    # print(f"{player_name} is entering game with hands {hand_str}")
                    # 开始事务
                    pipe.multi()

                    # 将 COUNT 数量加一
                    pipe.incr(f"{current_game_id}_COUNT")
                    
                    # 将玩家及其手牌加入当前游戏的 HANDS hash table
                    pipe.hset(f"{current_game_id}_HANDS", player_name, hand_str)

                    # 将奖池的值增加20
                    pipe.incrby(f"{current_game_id}_POOL", 20)

                    # 进行支付
                    
                    # 执行事务
                    pipe.execute()
                    break  # 如果事务执行成功，退出循环
                except redis.WatchError:
                    # 如果在事务执行期间键的值发生了变化，重试
                    continue


# 游戏引擎单例
def game_execution():

    # 获取CURRENT_GAME，拼接DEALER作为key，字符串存储荷官的五张手牌存储进入Redis
    current_game_id = redis_client.get("CURRENT_GAME")
    if current_game_id is None:
        raise ValueError("No current game found.")

    logger.info(f"Game ID: {current_game_id} executing")

    # 荷官随机五张牌，作为荷官手牌
    dealer_hand = generate_hand(5)
    dealer_hand_str = str(dealer_hand)  # 将手牌转换为字符串存储
    logger.info(f"Dealer's hand {dealer_hand_str} string")

    current_game_id = current_game_id.decode('utf-8')
    dealer_key = f"{current_game_id}_DEALER"
    redis_client.set(dealer_key, dealer_hand_str)

    # 设置荷官手牌过期时间
    redis_client.expire(dealer_key, 60 * 5)
    # 在redis中查询CURRENT_GAME_HANDS的所有玩家手牌，并设置过期时间
    hands_key = f"{current_game_id}_HANDS"
    player_hands = redis_client.hgetall(hands_key)

    scores_key = f"{current_game_id}_SCORES"

    # 计算和存储每个玩家的分数
    for player_name, hand in player_hands.items():
        print(hand)
        player_hand_str = hand.decode('utf-8')
        best_hand = combine_hands(dealer_hand_str, player_hand_str)
        best_hand_str = str(best_hand)
        print("best", best_hand_str)
        # 更新玩家最终手牌 _HANDS
        redis_client.hset(f"{current_game_id}_BEST_HANDS", player_name, best_hand_str)

        # 更新玩家得分 _SCORES
        player_score = int(calculate_score(best_hand))
        redis_client.zadd(scores_key, {player_name.decode('utf-8'): player_score})
    
    # 设置过期时间
    redis_client.expire(hands_key, 60 * 5)
    redis_client.expire(scores_key, 60 * 5)

    logger.info(f"Dealer's hand {dealer_hand} added to game {current_game_id}")

    player_scores = []
    # 打印每个玩家的分数
    for player_name, hand in player_hands.items():
        player_hand = hand.decode('utf-8')
        player_score = int(redis_client.zscore(scores_key, player_name.decode('utf-8')))
        player_scores.append((player_name.decode('utf-8'), player_score))
        logger.info(f"Player {player_name.decode('utf-8')}'s best hand {player_hand} with score {player_score}")
    
    # 计算奖励
    player_scores.sort(key=lambda x: x[1], reverse=True)  # 按分数从高到低排序
    num_players = len(player_scores)
    top_10_percent_index = max(1, math.floor(num_players * 0.1))
    top_25_percent_index = max(1, math.floor(num_players * 0.25))
    prize_pool = int(redis_client.get(f"{current_game_id}_POOL") or 0)
    top_10_percent_reward = int(prize_pool * 0.5 / top_10_percent_index) if top_10_percent_index > 0 else 0
    top_10_to_25_percent_reward = int(prize_pool * 0.35 / (top_25_percent_index - top_10_percent_index)) if top_25_percent_index > top_10_percent_index else 0

    rewards = {}
    for i, (player_name, player_score) in enumerate(player_scores):
        if i < top_10_percent_index:
            rewards[player_name] = top_10_percent_reward
        elif i < top_25_percent_index:
            rewards[player_name] = top_10_to_25_percent_reward
        else:
            rewards[player_name] = 0

    # 将奖励写入Redis中的_REWARDS有序集合
    rewards_key = f"{current_game_id}_REWARDS"
    with redis_client.pipeline() as pipe:
        while True:
            try:
                pipe.watch(rewards_key, "REWARD_RANKING_DAY")
                pipe.multi()
                for player, reward in rewards.items():
                    pipe.zadd(rewards_key, {player: reward})
                    # 更新每日排行信息
                    pipe.zincrby("REWARD_RANKING_DAY", reward, player)
                    # 为所有奖励不为0的玩家的items id为1的值增加奖励
                    if reward > 0:
                        player_tokens_key = f"{player}_TOKENS"
                        pipe.incrbyfloat(player_tokens_key, float(reward))
                pipe.execute()
                break
            except redis.WatchError:
                continue

    # 设置Rewards过期时间
    redis_client.expire(rewards_key, 60 * 5)
    
    # 异步保存游戏数据到 MongoDB
    threading.Thread(target=save_current_game_to_mongo, args=(current_game_id, dealer_hand_str, player_hands, rewards, prize_pool)).start()

    # 打印结果
    for player_name, hand in player_hands.items():
        player_hand = hand.decode('utf-8') # 从JSON字符串解析为列表
        player_score = int(redis_client.zscore(scores_key, player_name.decode('utf-8')))
        player_reward = int(redis_client.zscore(rewards_key, player_name.decode('utf-8')))
        logger.info(f"Player {player_name.decode('utf-8')}'s best hand {player_hand} with score {player_score} and reward {player_reward}")

def save_current_game_to_mongo(current_game_id, dealer_hand_str, player_hands, rewards, pool):
    # 保存当前游戏数据到 games 集合
    game_data = {
        "game_id": current_game_id,
        "pool": pool,
        "dealer_hand": dealer_hand_str,
        "players": [],
        "rewards": rewards,
        "timestamp": datetime.utcnow()
    }
    for player_name, hand in player_hands.items():
        player_hand = hand.decode('utf-8')
        player_score = int(redis_client.zscore(f"{current_game_id}_SCORES", player_name.decode('utf-8')))
        player_reward = int(rewards.get(player_name.decode('utf-8'), 0))
        player_tokens_key = f"{player_name.decode('utf-8')}_TOKENS"
        game_data["players"].append({
            "name": player_name.decode('utf-8'),
            "hand": player_hand,
            "score": player_score,
            "reward": player_reward
        })
        
        # 更新玩家的 history
        player_history_entry = {
            "game_id": current_game_id,
            "hand": player_hand,
            "score": player_score,
            "reward": player_reward
        }
        db.players.update_one(
            {"name": player_name.decode('utf-8')},
            {"$push": {"history": player_history_entry}},
            upsert=True
        )

    db.games.insert_one(game_data)

# 将 Redis 中的 player_ITEMS 数据持久化到 MongoDB 中
def persist_player_items_to_mongo(player_name: str):
    player_items_key = f"{player_name}_ITEMS"
    player_items = redis_client.hgetall(player_items_key)
    
    if player_items:
        # 转换 Redis 数据为 Python 字典
        player_items = {key.decode('utf-8'): int(value.decode('utf-8')) for key, value in player_items.items()}
        
        # 检查 MongoDB 中是否存在该玩家
        player_collection = db.players
        existing_player = player_collection.find_one({"name": player_name})
        
        if existing_player:
            # 更新现有玩家的 items
            player_collection.update_one({"name": player_name}, {"$set": {"items": player_items}})
        else:
            # 插入新玩家
            new_player = {"name": player_name, "items": player_items}
            player_collection.insert_one(new_player)

def update_player_tokens_to_mongo(player_name: str):
    player_tokens_key = f"{player_name}_TOKENS"
    player_tokens = redis_client.get(player_tokens_key)
    
    if player_tokens:
        # Convert Redis data to float
        player_tokens = float(player_tokens.decode('utf-8'))
        
        # Check if the player exists in MongoDB
        player_collection = db.players
        existing_player = player_collection.find_one({"name": player_name})
        
        if existing_player:
            # Update existing player's tokens
            player_collection.update_one({"name": player_name}, {"$set": {"tokens": player_tokens}})
        else:
            # Insert new player with tokens
            new_player = {"name": player_name, "tokens": player_tokens}
            player_collection.insert_one(new_player)

def update_player(player_name: str):
    player_tokens_key = f"{player_name}_TOKENS"
    player_items_key = f"{player_name}_ITEMS"
    player_tokens = redis_client.get(player_tokens_key)
    player_items = redis_client.hgetall(player_items_key)

    update_data = {}
    if player_tokens:
        player_tokens = float(player_tokens.decode('utf-8'))
        update_data["tokens"] = player_tokens

    if player_items:
        player_items = {key.decode('utf-8'): int(value.decode('utf-8')) for key, value in player_items.items()}
        update_data["items"] = player_items

    if update_data:
        db.players.update_one({"name": player_name}, {"$set": update_data}, upsert=True)
        logger.info(f"Updated {player_name}'s tokens and items in MongoDB")

def check_task_completion(player_task_record, refresh_hours):
    last_completed = player_task_record.get("last_completed")
    if last_completed:
        last_completed = datetime.strptime(last_completed, '%Y-%m-%d %H:%M:%S')
        refresh_time = timedelta(hours=refresh_hours)
        if datetime.utcnow() < last_completed + refresh_time:
            remain_time = last_completed + refresh_time - datetime.utcnow()
            hours, remainder = divmod(remain_time.total_seconds(), 3600)
            minutes, seconds = divmod(remainder, 60)
            formatted_remaining_time = f"{int(hours)}:{int(minutes)}:{int(seconds)}"
            return False, formatted_remaining_time
    return True, None

def fetch_type_tasks(task_type: int):
    # Retrieve all task IDs of a specific type from Redis
    task_ids = redis_client.smembers(f"task_type:{task_type}")
    tasks = []
    
    for task_id in task_ids:
        # Construct the key for each task
        task_key = f"task:{task_id.decode('utf-8')}"
        # Retrieve task data from Redis
        task_data = redis_client.hgetall(task_key)
        # Convert task data to the appropriate format
        formatted_task_data = {key.decode('utf-8'): value.decode('utf-8') for key, value in task_data.items()}
        tasks.append(formatted_task_data)
    
    # Sort tasks by 'checkpoint' key, assuming it's an integer
    tasks.sort(key=lambda x: int(x['checkpoint']))
    
    return tasks

def settle_rewards(player_name: str, checkpoint: int, task_type: int) -> bool:
    """
    Settle rewards for a player based on the checkpoint and task type, returning success status.
    
    Args:
    player_name (str): The name of the player.
    checkpoint (int): The checkpoint to match.
    task_type (int): The type of tasks to filter by.
    settlement_type (int): The type of settlement; default is 1.
    
    Returns:
    bool: True if rewards were successfully given, False otherwise.
    """
    # Retrieve all task IDs of the specified type from Redis
    task_ids = redis_client.smembers(f"task_type:{task_type}")
    
    for task_id in task_ids:
        # Construct the key for each task
        task_key = f"task:{task_id.decode('utf-8')}"
        # Retrieve task data from Redis
        task_data = redis_client.hgetall(task_key)
        # Convert task data to the appropriate format
        formatted_task_data = {key.decode('utf-8'): value.decode('utf-8') for key, value in task_data.items()}
        
        # Check if the checkpoint matches
        if int(formatted_task_data['checkpoint']) == checkpoint:
            # Decode and evaluate the rewards string to convert it into a dictionary
            rewards = eval(formatted_task_data['rewards'])
            # Call send_rewards to reward the player and capture the result
            success = send_rewards(player_name=player_name, rewards=rewards, task_id=task_id.decode('utf-8'))
            return success  # Return the result of sending rewards

    return False  # Return False if no matching task was found or rewards were not sent

def update_can_claim_tasks(player_name: str, task_type: str):
    # Fetch player's longest consecutive checkins from Redis
    longest_checkin_key = f"{player_name}_LONGEST_CHECKIN"
    longest_checkin = int(redis_client.get(longest_checkin_key) or 0)

    # Fetch task IDs of the specified type from Redis
    task_ids = redis_client.smembers(f"task_type:{task_type}")
    can_claim = {task.decode('utf-8') for task in redis_client.smembers(f"{player_name}_CANCLAIM")}
    print(f"can_claim, {can_claim}")
    claimed = {task.decode('utf-8') for task in redis_client.smembers(f"{player_name}_CLAIMED")}
    print(f"claimed, {claimed}")
    # Determine new tasks that can be claimed based on the longest checkin
    new_can_claim = []
    for task_id in task_ids:
        task_id_str = task_id.decode('utf-8')
        task_key = f"task:{task_id_str}"
        checkpoint_data = redis_client.hget(task_key, 'checkpoint')
        print(f"checkpoint_data, {checkpoint_data}")
        if checkpoint_data:
            checkpoint = int(checkpoint_data.decode('utf-8'))
            print(f"inside_task_id, {task_id_str}")
            if task_id_str not in can_claim and task_id_str not in claimed and longest_checkin >= checkpoint:
                print(f"not in, {checkpoint}, {task_id_str}")
                new_can_claim.append(task_id_str)
                can_claim.add(task_id_str)

    # Update CANCLAIM in Redis
    if new_can_claim:
        redis_client.sadd(f"{player_name}_CANCLAIM", *new_can_claim)

    # Sync CANCLAIM with MongoDB
    db.players.update_one(
        {"name": player_name},
        {"$set": {"can_claim": list(can_claim)}}
    )

    return list(new_can_claim)

async def is_type2(task_id):
    """
    Check if a task ID belongs to type 2 by looking up the 'checkin:2' hashmap in Redis.
    """
    # Check if the task_id exists in the 'checkin:2' hashmap
    exists = redis_client.hexists("checkin:2", task_id)
    return exists

def send_rewards(player_name: str, rewards: Optional[list] = None, task_id: Optional[str] = None) -> bool:
    """
    Update player's rewards in Redis atomically.
    Args:
    player_name (str): The name of the player.
    rewards (Optional[list]): An optional list of tuples where each tuple contains an item_id and quantity.
    task_id (Optional[str]): The task identifier, if applicable.

    Returns:
    bool: True if the transaction was successful, False otherwise.
    """
    try:
        with redis_client.pipeline() as pipe:
            # 非任务奖励：直发
            if rewards:
                for item_id, quantity in rewards:
                    if item_id == 1:
                        # 每日排行榜
                        pipe.zincrby("REWARD_RANKING_DAY", quantity, player_name)
                        pipe.incrbyfloat(f"{player_name}_TOKENS", float(quantity))
                    else:
                        pipe.hincrby(f"{player_name}_ITEMS", str(item_id), int(quantity))
            # 任务奖励，从表中获取奖励，根据结算类型，判断是否直发
            if task_id:
                rewards = redis_client.hget(f"task:{task_id}", "rewards")
                if rewards:
                    rewards_list = eval(rewards.decode('utf-8'))
                    send_rewards(player_name, rewards_list)
                settlement_type = int(redis_client.hget(f"task:{task_id}", "settlement_type").decode('utf-8'))
                if settlement_type == 1:
                    pipe.srem(f"{player_name}_CANCLAIM", task_id)
                    pipe.sadd(f"{player_name}_CLAIMED", task_id)
                elif settlement_type == 2:
                    pipe.srem(f"{player_name}_CANCLAIM", task_id)
            pipe.execute()
        return True
    except Exception as e:
        print(f"Failed to update rewards: {e}")
        return False

def fetch_claim_tasks(player_name: str, task_type: Optional[int] = None, claim_type: str = "CANCLAIM") -> List[int]:
    """
    Fetches task IDs from CANCLAIM set for a given player that match a specific task type, or all task IDs if no type is specified.
    
    Args:
    player_name (str): The name of the player.
    task_type (Optional[int]): The type of tasks to filter by, or None to fetch all tasks.
    
    Returns:
    List[int]: A list of task IDs that the player can claim, filtered by type if specified.
    """
    # Fetch all task IDs from CANCLAIM
    tasks = redis_client.smembers(f"{player_name}_{claim_type}")
    print(f"tasks in {tasks}")
    if task_type is not None:
        # Fetch task IDs of the specified type
        type_tasks = redis_client.smembers(f"task_type:{task_type}")
        # Filter tasks by the specified type
        result = [int(task_id.decode('utf-8')) for task_id in tasks if task_id in type_tasks]
    else:
        # Return all tasks if no type is specified
        result = [int(task_id.decode('utf-8')) for task_id in tasks]
    
    return result

def fetch_random_quests(settle_num: int) -> List[int]:
    """
    Fetches n random quest IDs of type 1 for a given player.
    
    Args:
    player_name (str): The name of the player.
    n (int): The number of random quest IDs to fetch.
    
    Returns:
    List[int]: A list containing n random quest IDs of type 1.
    """
    # Fetch all quest IDs of type 1
    type_1_settles = redis_client.smembers(f"settlement_type:1")
    type_1_settles = [int(quest_id.decode('utf-8')) for quest_id in type_1_settles]
    
    # Randomly select n quest IDs
    random_settles = random.sample(type_1_settles, min(settle_num, len(type_1_settles)))
    
    return random_settles

def settlement_process(settlement_num: int) -> List[List[int]]:
    """
    Settlement process that fetches n random quest IDs of type 1 and places them in the first position of the settlement array.
    
    Args:
    player_name (str): The name of the player.
    n (int): The number of random quest IDs to fetch.
    
    Returns:
    List[List[int]]: The settlement array with the random quest IDs at the first position.
    """
    settlement_array = []
    
    # Fetch n random quest IDs of type 1
    random_settle = fetch_random_quests(settlement_num)
    
    # Place the random quest IDs in the first position of the settlement array
    settlement_array.append(random_settle)
    
    return settlement_array

def global_settlement_execute(settlement_array: List[List[int]]) -> List[Dict]:
    """
    Executes global settlement by fetching information for each settlement ID in the first element of the settlement array.

    Args:
    settlement_array (List[List[int]]): The settlement array containing settlement IDs in the first element.

    Returns:
    List[Dict]: A list of dictionaries containing information about each settlement.
    """
    settlement_ids = settlement_array[0]
    settlement_info_list = []

    # Fetch information for each settlement ID
    for settlement_id in settlement_ids:
        settlement_info = redis_client.hgetall(f"settlement_info:{settlement_id}")
        settlement_info_decoded = {key.decode('utf-8'): value.decode('utf-8') for key, value in settlement_info.items()}
        settlement_info_list.append(settlement_info_decoded)

    return settlement_info_list

def generate_and_store_invite_code(player_name: str) -> str:
    """
    Generates a unique 6-character invite code consisting of uppercase English letters and digits for a player and stores it in Redis.

    Args:
    player_name (str): The name of the player for whom the invite code is being generated.

    Returns:
    str: The generated invite code, which will be a combination of 6 uppercase English letters and digits (e.g., 'A1B2C3').
    """
    import random
    import string

    # Generate a unique invite code using uppercase letters and digits
    invite_code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))

    # Store the invite code in Redis with a key specific to the player
    redis_client.set(f"{player_name}_INVITE_CODE", invite_code)

    return invite_code


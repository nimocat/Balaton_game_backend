import threading
import time
import random
import json
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

console = logging.StreamHandler()
console.setLevel(logging.INFO)

logger.addHandler(handler)
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
    
    # 创建一个 Redis 事务（Pipeline）
    with redis_client.pipeline() as pipe:
        while True:
            try:
                # Watch the keys that will be modified
                pipe.watch(f"{current_game}_HANDS", f"{current_game}_POOL", f"{player_name}_ITEMS", f"{current_game}_COUNT")

                # 开始事务
                pipe.multi()

                # 将玩家及其对应的手牌加入当前游戏的 HANDS hash table
                pipe.hset(f"{current_game}_HANDS", player_name, hand_str)

                # 将 POOL 的数字增加相应的 cost
                pipe.incrby(f"{current_game}_POOL", cost)

                # 注意，玩家需要在连接完钱包或者进入界面时，就把他的信息加载到redis中
                # 将玩家的 ITEMS 中的 token 数量减少相应的 cost
                tokens = redis_client.hget(player_items_key, "1")
                if tokens is None or int(tokens) < cost:
                    return {"error": "Insufficient tokens"}
                
                pipe.hincrby(player_items_key, "1", -cost)

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
                        player_items_key = f"{player}_ITEMS"
                        pipe.hincrby(player_items_key, "1", reward)
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

def get_checkin_data(check_in_type):
    # Retrieve all checkin tasks of type '1' from Redis and format them into JSON
    checkin_type_one_keys = redis_client.keys(f"checkin:{check_in_type}")
    checkin_type_one_tasks = []
    
    for key in checkin_type_one_keys:
        task_data = redis_client.hgetall(key)
        for checkpoint, rewards in task_data.items():
            try:
                checkpoint_int = int(checkpoint)
                rewards_str = rewards.decode('utf-8')
            except ValueError:
                continue  # Skip this iteration if conversion to int fails
            task = {
                "checkpoint": checkpoint_int,
                "rewards": rewards_str
            }
            checkin_type_one_tasks.append(task)
    return checkin_type_one_tasks

def update_can_claim_tasks(player_name):
    # Fetch player's consecutive checkins from MongoDB
    player_data = db.players.find_one({"name": player_name})
    consecutive_checkins = player_data.get('consecutive_checkins', 0)

    # Fetch type 2 checkin tasks from Redis
    type_two_tasks = redis_client.hgetall("checkin:2")
    can_claim = set(redis_client.smembers(f"{player_name}_CANCLAIM"))
    claimed = set(redis_client.smembers(f"{player_name}_CLAIMED"))

    # Determine new tasks that can be claimed
    new_can_claim = []
    for checkpoint, task_id in type_two_tasks.items():
        checkpoint_int = int(checkpoint)
        task_id_str = task_id.decode('utf-8')

        if consecutive_checkins >= checkpoint_int and task_id_str not in can_claim and task_id_str not in claimed:
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


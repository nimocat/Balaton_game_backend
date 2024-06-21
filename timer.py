import asyncio
import json
import threading
import time
import random
import aioredis
from models.game import Game
from utils.pre_loads import load_data_from_files
import redis
import math
import threading
import logging
import pandas as pd
from logging.handlers import RotatingFileHandler
from datetime import datetime, timedelta
from bson import ObjectId
from database import db, redis_client
from alg import generate_hand
from game_logic import save_current_game_to_mongo, update_player_tokens_to_mongo, send_rewards

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

CURRENT_GAME = "CURRENT_GAME"
LAST_GAME = "LAST_GAME"
DURATION = 30 # 过期时间，和游戏的单局游戏时间完全一致

# 游戏引擎单例
async def start_new_game(redis_client):

    # # 检查是否已存在游戏ID
    # if redis_client.get(CURRENT_GAME):
    #     return  # 如果CURRENT_GAME已存在，不执行任何操作

    # 生成game_id
    game_id = datetime.utcnow().strftime('%Y%m%d%H%M%S%f')

    await redis_client.set(CURRENT_GAME, game_id)
    await redis_client.set(LAST_GAME, game_id)
    # 设置过期时间，如果查询不到CURRENT_GAME，则为游戏结算中，未开始新游戏。如果查询到的CURRENT_GAME和客户端存储的game_id不同，则说明已经开始一局新游戏
    await redis_client.expire(CURRENT_GAME, DURATION)
    await redis_client.publish("countdown_channel", f"Countdown started for {CURRENT_GAME} with duration {DURATION} seconds")

    # 荷官随机五张牌，作为荷官手牌
    dealer_hand = generate_hand(5)
    dealer_hand_str = str(dealer_hand)  # 将手牌转换为字符串存储
    dealer_key = f"{game_id}_DEALER"
    await redis_client.set(dealer_key, dealer_hand_str)
    logger.info(f"Game ID: {game_id} Generated, New Game Start, Dealer Hand: {dealer_hand_str}")

    # 存入数据库，所有基于redis的新数据添加，都根据CURRENT_GAME这个值来进行

# 游戏引擎-单例执行
async def game_execution():
    print('game executing')
    # 获取CURRENT_GAME，拼接DEALER作为key，字符串存储荷官的五张手牌存储进入Redis
    current_game_id = redis_client.get(LAST_GAME)
    if current_game_id is None:
        raise ValueError("No current game found.")

    logger.info(f"Game ID: {current_game_id} executing")

    current_game_id = current_game_id.decode('utf-8')
    dealer_key = f"{current_game_id}_DEALER"
    dealer_hand = redis_client.get(dealer_key).decode('utf-8')
    dealer_hand_str = str(dealer_hand)  # 将手牌转换为字符串存储
    # await websocket_manager.broadcast(dealer_hand_str, game_only=True)  # Serialize to JSON string
    logger.info(f"Dealer's hand {dealer_hand_str} string")
    # 设置荷官手牌过期时间
    redis_client.expire(dealer_key, 60 * 5)
    # 在redis中查询CURRENT_GAME_HANDS的所有玩家手牌，并设置过期时间
    hands_key = f"{current_game_id}_HANDS"
    player_hands = redis_client.hgetall(hands_key)

    scores_key = f"{current_game_id}_SCORES"

    # 设置过期时间
    redis_client.expire(hands_key, 60 * 5)
    redis_client.expire(scores_key, 60 * 5)

    player_scores = []
    # 打印每个玩家的分数
    for player_name, hand in player_hands.items():
        player_hand = hand.decode('utf-8')
        print(player_name, hand)
        player_score = int(redis_client.zscore(scores_key, player_name.decode('utf-8')))
        player_scores.append((player_name.decode('utf-8'), player_score))
    
    # 计算奖励
    player_scores.sort(key=lambda x: x[1], reverse=True)  # 按分数从高到低排序
    num_players = len(player_scores)
    top_10_percent_index = max(1, math.floor(num_players * 0.1))
    top_35_percent_index = max(1, math.floor(num_players * 0.35))
    prize_pool = int(redis_client.get(f"{current_game_id}_POOL") or 0)
    # 计算出奖励
    top_10_percent_reward = float(prize_pool * 0.5 / top_10_percent_index) if top_10_percent_index > 0 else 0
    top_10_to_25_percent_reward = float(prize_pool * 0.35 / (top_35_percent_index - top_10_percent_index)) if top_35_percent_index > top_10_percent_index else 0

    rewards = {}
    for i, (player_name, player_score) in enumerate(player_scores):
        if i < top_10_percent_index:
            rewards[player_name] = round(top_10_percent_reward, 2)
        elif i < top_35_percent_index:
            rewards[player_name] = round(top_10_to_25_percent_reward, 2)
        else:
            rewards[player_name] = 0

    # 将奖励写入Redis中的_REWARDS有序集合
    rewards_key = f"{current_game_id}_REWARDS"
    with redis_client.pipeline() as pipe:
        while True:
            try:
                for player, reward in rewards.items():
                    pipe.zadd(rewards_key, {player: reward})
                    # 为所有奖励不为0的玩家的items id为1的值增加奖励
                    if reward > 0:
                        send_rewards(player_name=player, rewards =[[1, reward]]) # 奖励直发
                pipe.execute()
                break
            except redis.WatchError:
                continue

    # 设置Rewards过期时间
    redis_client.expire(rewards_key, 60 * 5)
    
    # 异步保存游戏数据到 MongoDB
    threading.Thread(target=save_current_game_to_mongo, args=(current_game_id, dealer_hand_str, player_hands, rewards, prize_pool)).start()
    # 更新所有玩家的_TOKENS信息到MongoDB

    def update_player_tokens():
        for player_name, _ in player_scores:
            update_player_tokens_to_mongo(player_name)

    threading.Thread(target=update_player_tokens).start()
    
    # 打印结果
    for player_name, hand in player_hands.items():
        player_hand = hand.decode('utf-8') # 从JSON字符串解析为列表
        player_score = int(redis_client.zscore(scores_key, player_name.decode('utf-8')))
        player_reward = float(redis_client.zscore(rewards_key, player_name.decode('utf-8')))
        logger.info(f"Player {player_name.decode('utf-8')}'s best hand {player_hand} with score {player_score} and reward {player_reward}")

# async def broadcast_game_result():
#     print(f"[Results Boradcasting] {websocket_manager.current_game_websockets}")

#     game_id = redis_client.get("LAST_GAME").decode('utf-8')
#     sockets_key = f"{game_id}_SOCKETS"
#     all_sockets = redis_client.hgetall(sockets_key)
    
#     for socket_id, player_name in all_sockets.items():
#         print(f"socket_id: {socket_id}, player_name: {player_name}")
#         player_name = player_name.decode('utf-8')
#         game_info_response = await Game.getEndedGameInfo(game_id, player_name)
#         data = {"type": "ended_game_info", "data": game_info_response}
#         # Retrieve the websocket using the socket_id
#         websocket = websocket_manager.current_game_websockets.get(socket_id)
#         if websocket:
#             print(f"[Boradcasting] Broadcast to Player {player_name} with Socket ID {socket_id}")
#             await websocket.send_text(json.dumps(data))

async def countdown_expiry_listener(redis):
    pubsub = redis.pubsub()
    await pubsub.psubscribe("__keyevent@0__:expired")

    async for message in pubsub.listen():
        if message['type'] == 'pmessage':
            data = message['data']
            if data.endswith("_FARMING"):
                player_name = data[:-8]  # Correct the slice to remove '_FARMING'
                threading.Thread(target=add_task_to_can_claim, args=(player_name, 301)).start()
            if data == "CURRENT_GAME":
                await game_execution()
                last_game_id = redis_client.get("LAST_GAME").decode('utf-8')
                await redis.publish('endgameinfo', last_game_id)
                await start_new_game(redis)

    await pubsub.close()

def add_task_to_can_claim(player_name: str, task_id: int):
    can_claim_key = f"{player_name}_CANCLAIM"
    redis_client.sadd(can_claim_key, task_id)
    logger.info(f"Task {task_id} added to {player_name}'s CANCLAIM list")

async def main():
    # Create an asynchronous Redis connection
    redis = await aioredis.from_url("redis://localhost", encoding="utf-8", decode_responses=True)
    # Use the asynchronous Redis client for getting the current game
    current_game = await redis.get("CURRENT_GAME")
    if current_game is None:
        await start_new_game(redis)

    await countdown_expiry_listener(redis)  # Pass the redis client to the listener

    # Close the Redis connection when done
    redis.close()
    await redis.wait_closed()

if __name__ == "__main__":
    asyncio.run(main())


from fastapi import FastAPI, HTTPException
from datetime import datetime, timedelta
from bson import ObjectId
import threading
import time
import random
from routes import router
from database import db, redis_client
from models import Player
from alg import generate_hand, calculate_score, combine_hands, dealer_draw
# from game_logic import player_entry
app = FastAPI()
app.include_router(router)

current_game = None
current_game_lock = threading.Lock()
prize_pool = 0

def start_new_game():
    global current_game
    with current_game_lock:
        game_id = datetime.utcnow().strftime('%Y%m%d%H%M%S%f')
        current_game = {
            "game_id": game_id,
            "dealer_hand": [],
            "players": [],
            "start_time": datetime.utcnow()
        }
        print("CURRENT_GAME_ID", game_id)
        db.games.insert_one(current_game)
        # redis_client = RedisConnection.get_instance().client
        redis_client.set("CURRENT_GAME", game_id)

def game_execution():
    # 荷官随机五张牌，作为荷官手牌
    dealer_hand = generate_hand(5)

    # 获取CURRENT_GAME，拼接DEALER作为key，字符串存储荷官的五张手牌存储进入Redis
    current_game_id = redis_client.get("CURRENT_GAME")
    if current_game_id is None:
        raise ValueError("No current game found.")

    dealer_key = f"{current_game_id.decode('utf-8')}_DEALER"
    redis_client.set(dealer_key, "hand", ' '.join(dealer_hand))

    # 在redis中查询CURRENT_GAME_HANDS的所有玩家手牌
    hands_key = f"{current_game_id.decode('utf-8')}_HANDS"
    player_hands = redis_client.hgetall(hands_key)

    scores_key = f"{current_game_id.decode('utf-8')}_SCORES"

    # Calculate and store each player's score
    for player_name, hand in player_hands.items():
        player_hand = hand.decode('utf-8').split(' ')
        best_hand = combine_hands(dealer_hand, player_hand)
        player_score = calculate_score(best_hand)
        redis_client.zadd(scores_key, {player_name.decode('utf-8'): player_score})

    print(f"Dealer's hand {dealer_hand} added to game {current_game_id.decode('utf-8')}")
    for player_name, hand in player_hands.items():
        player_hand = hand.decode('utf-8').split(' ')
        player_score = redis_client.zscore(scores_key, player_name.decode('utf-8'))
        print(f"Player {player_name.decode('utf-8')}'s best hand {best_hand} with score {player_score}")


def player_to_dict(player):
    return {
        "name": player.name,
        "hand": player.hand,
        "score": 0,  # 初始分数为0
        "reward": 0,  # 初始奖励为0
        "_id": ObjectId(),
        "game_id": current_game["game_id"],
        "game_ids": []  # 初始化game_ids字段
    }

def player_entry():
    while True:
        time.sleep(random.uniform(0.5, 2))  # 更快的随机等待时间，模拟玩家随机进入游戏
        player_name = f"Player{len(current_game['players']) + 1}"
        player = Player(player_name)
        global prize_pool
        prize_pool += 20
        with current_game_lock:
            existing_player = db.players.find_one({"name": player_name})
            if existing_player:
                player_dict = existing_player
                db.players.update_one(
                    {"name": player_name},
                    {"$addToSet": {"game_ids": current_game["game_id"]}}
                )
            else:
                player_dict = player_to_dict(player)
                player_dict["game_ids"].append(current_game["game_id"])
                db.players.insert_one(player_dict)
            
            current_game["players"].append(player_dict)
            db.games.update_one(
                {"game_id": current_game["game_id"]},
                {"$push": {"players": player_dict}}
            )

def execute_function():
    global current_game
    with current_game_lock:
        if current_game and current_game["players"]:
            print(f"5-second timer ended. Number of players this round: {len(current_game['players'])}, Prize Pool: ${prize_pool}")
            dealer_hand = dealer_draw()
            current_game["dealer_hand"] = dealer_hand
            print("Dealer's hand:", dealer_hand)
            scores = []
            for player in current_game["players"]:
                combined_hand = player["hand"] + dealer_hand
                score = calculate_score(combined_hand)
                reward = calculate_reward(score)
                player["score"] = score
                player["reward"] = reward
                db.players.update_one(
                    {"_id": player["_id"]},
                    {"$set": {"score": score, "reward": reward}}
                )
                scores.append((player["_id"], player["name"], score))
                print(f"Player {player['name']} combined hand: {combined_hand}, Score: {score}")

            print("Length of scores", len(scores))
            
            scores.sort(key=lambda x: x[2], reverse=True)
            ranking = {str(player_id): {"name": name, "score": score} for player_id, name, score in scores}
            print("Ranking list:")
            for player_id, entry in ranking.items():
                print(f"{entry['name']}: {entry['score']}")

            print("Length of ranking", len(ranking))

            db.games.update_one(
                {"game_id": current_game["game_id"]},
                {"$set": {
                    "dealer_hand": dealer_hand,
                    "end_time": datetime.utcnow(),
                    "players": current_game["players"],
                    "ranking": ranking
                }}
            )

            # 更新每个玩家的 game_ids 字段
            for player in current_game["players"]:
                db.players.update_one(
                    {"_id": player["_id"]},
                    {"$addToSet": {"game_ids": current_game["game_id"]}}
                )

    # 启动新的一局游戏
    start_new_game()


def countdown_timer():
    countdown_time = timedelta(seconds=5)  # 这里使用5秒进行测试
    while True:
        end_time = datetime.now() + countdown_time
        while True:
            current_time = datetime.now()
            remaining_time = end_time - current_time
            if remaining_time <= timedelta(seconds=0):
                break
            print(f"Current time: {current_time.strftime('%Y-%m-%d %H:%M:%S')} - Time remaining: {str(remaining_time).split('.')[0]}")
            time.sleep(1)
        
        execute_function()
        print("Resetting timer to 5 seconds for testing.")
        print("-----------")

def calculate_reward(score):
    # 简单的奖励计算逻辑，可根据实际情况调整
    return score

def serialize_objectid(data):
    if isinstance(data, list):
        return [serialize_objectid(item) for item in data]
    elif isinstance(data, dict):
        return {key: serialize_objectid(value) for key, value in data.items()}
    elif isinstance(data, ObjectId):
        return str(data)
    elif isinstance(data, datetime):
        return data.isoformat()
    else:
        return data

if __name__ == "__main__":
    start_new_game()
    
    # 模拟启动玩家进入游戏的线程，在正式服务器中删除 // mock
    for _ in range(10):
        player_thread = threading.Thread(target=player_entry)
        player_thread.daemon = True
        player_thread.start()

    # 启动倒计时线程
    countdown_thread = threading.Thread(target=countdown_timer)
    countdown_thread.daemon = True
    countdown_thread.start()

    # 启动FastAPI应用
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
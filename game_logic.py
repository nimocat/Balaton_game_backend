import threading
import time
import random
from datetime import datetime, timedelta
from bson import ObjectId
from database import db
from models import Player
from algorithm import calculate_score, calculate_reward, dealer_draw

current_game = None
current_game_lock = threading.Lock()

def start_new_game():
    global current_game
    with current_game_lock:
        game_id = str(ObjectId())
        current_game = {
            "game_id": game_id,
            "dealer_hand": [],
            "players": [],
            "start_time": datetime.utcnow()
        }
        db.games.insert_one(current_game)

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

def player_entry(current_game):
    while True:
        time.sleep(random.uniform(0.5, 2))  # 更快的随机等待时间，模拟玩家随机进入游戏
        player_name = f"Player{len(current_game['players']) + 1}"
        player = Player(player_name)
        player_dict = player_to_dict(player, current_game)

        with current_game_lock:
            current_game["players"].append(player_dict)
            db.players.insert_one(player_dict)
            db.games.update_one(
                {"game_id": current_game["game_id"]},
                {"$push": {"players": player_dict}}
            )

def execute_function():
    global current_game
    with current_game_lock:
        if current_game and current_game["players"]:
            print(f"5-second timer ended. Number of players this round: {len(current_game['players'])}")
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

            for player in current_game["players"]:
                db.players.update_one(
                    {"_id": player["_id"]},
                    {"$addToSet": {"game_ids": current_game["game_id"]}}
                )

    start_new_game()

def countdown_timer():
    countdown_time = timedelta(seconds=5)
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

def start_game_threads():
    start_new_game()
    
    for _ in range(10):
        player_thread = threading.Thread(target=player_entry)
        player_thread.daemon = True
        player_thread.start()

    countdown_thread = threading.Thread(target=countdown_timer)
    countdown_thread.daemon = True
    countdown_thread.start()
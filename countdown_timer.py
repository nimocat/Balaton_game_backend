import time
from datetime import datetime, timedelta
import threading
import random
from poker import Player, game_round, dealer_draw, calculate_score

players = []
players_lock = threading.Lock()

def player_entry():
    while True:
        time.sleep(random.uniform(0.5, 2))  # 更快的随机等待时间，模拟玩家随机进入游戏
        player_name = f"Player{len(players) + 1}"
        player = Player(player_name)
        with players_lock:
            players.append(player)

def execute_function():
    with players_lock:
        if players:
            num_players = len(players)
            reward_pool = num_players * 20  # 每个玩家支付20进入奖池
            top_10_percent = max(1, num_players // 10)
            top_35_percent = max(1, num_players * 35 // 100)

            print(f"5-second timer ended. Number of players this round: {num_players}")
            dealer_hand = dealer_draw()
            print("Dealer's hand:", dealer_hand)
            scores = []
            for player in players:
                combined_hand = player.hand + dealer_hand
                score = calculate_score(combined_hand)
                scores.append((player.name, score))
                print(f"Player {player.name} combined hand: {combined_hand}, Score: {score}")
            
            scores.sort(key=lambda x: x[1], reverse=True)
            print("Ranking list:")
            for name, score in scores:
                print(f"{name}: {score}")

            # 分配奖池奖金
            print(f"Total reward pool: {reward_pool}")
            winners_10_percent = scores[:top_10_percent]
            winners_35_percent = scores[top_10_percent:top_35_percent]
            
            reward_10_percent = (reward_pool * 50) // 100 // top_10_percent
            reward_35_percent = (reward_pool * 35) // 100 // (top_35_percent - top_10_percent)
            treasury_amount = reward_pool * 15 // 100

            print(f"Top 10% players (reward {reward_10_percent} each):")
            for winner in winners_10_percent:
                print(f"{winner[0]}: {reward_10_percent}")

            print(f"10%-35% players (reward {reward_35_percent} each):")
            for winner in winners_35_percent:
                print(f"{winner[0]}: {reward_35_percent}")

            print(f"Treasury amount: {treasury_amount}")

            players.clear()
        else:
            print("No players in the game.")
def countdown_timer():
    countdown_time = timedelta(seconds=15)  # 这里使用5秒进行测试
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

if __name__ == "__main__":
    # 启动10个线程来模拟玩家快速进入
    for _ in range(5):
        player_thread = threading.Thread(target=player_entry)
        player_thread.daemon = True
        player_thread.start()

    countdown_timer()
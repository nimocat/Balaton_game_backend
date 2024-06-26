import random
import itertools
import math
from database import redis_client
import json

# 定义扑克牌，包括大小王
suits = ['H', 'S', 'D', 'C']  # 红桃, 黑桃, 方块, 梅花
ranks = ['2', '3', '4', '5', '6', '7', '8', '9', 'T', 'J', 'Q', 'K', 'A']
jokers = ['BJ', 'RJ']  # 大小王，BJ: Black Joker, RJ: Red Joker

def generate_hand(poker_num):
    deck = [suit + rank for suit in suits for rank in ranks] + jokers
    random.shuffle(deck)
    return deck[:poker_num]

def dealer_draw():
    return generate_hand(5)

def calculate_score(hand):
    # print(hand)
    joker_ranks = ranks + ['BJ', 'RJ']

    def is_flush(hand):
        suit = hand[0][0]
        return all(card[0] == suit for card in hand if card not in ['BJ', 'RJ'])

    def is_straight(hand):
        rank_indices = sorted([joker_ranks.index(card[1:]) for card in hand if card not in ['BJ', 'RJ']])
        for i in range(len(rank_indices) - 1):
            if rank_indices[i + 1] - rank_indices[i] != 1:
                return False
        return True

    def is_straight_flush(hand):
        return is_straight(hand) and is_flush(hand)

    def is_royal_flush(hand):
        return is_straight_flush(hand) and set(card[1:] for card in hand if card not in ['BJ', 'RJ']) == {'T', 'J', 'Q', 'K', 'A'}

    def get_rank_counts(hand):
        hand_ranks = [card[1:] for card in hand if card not in ['BJ', 'RJ']]
        rank_counts = {rank: hand_ranks.count(rank) for rank in ranks}
        joker_count = sum(card in ['BJ', 'RJ'] for card in hand)
        return rank_counts, joker_count

    def replace_jokers(hand, replacements):
        new_hand = []
        joker_index = 0
        for card in hand:
            if card in ['BJ', 'RJ']:
                new_hand.append(f"{hand[joker_index][0]}{replacements[joker_index]}")
                joker_index += 1
            else:
                new_hand.append(card)
        return new_hand

    rank_counts, joker_count = get_rank_counts(hand)
    possible_scores = []

    if joker_count > 0:
        for replacements in itertools.product(ranks, repeat=joker_count):
            new_hand = replace_jokers(hand, replacements)
            # print("new_hand", new_hand)
            rank_counts, _ = get_rank_counts(new_hand)
            possible_scores.append(calculate_score_without_joker(rank_counts, new_hand))
    else:
        possible_scores.append(calculate_score_without_joker(rank_counts, hand))

    return max(possible_scores)

def combine_hands(dealer_hand, player_hand):
    # Convert string representations of hands into lists
    print(dealer_hand)
    print(player_hand)
    dealer_hand_list = eval(dealer_hand)
    player_hand_list = eval(player_hand)
    
    # Combine dealer's hand with player's hand
    combined_hands = dealer_hand_list + player_hand_list
    
    # Find the best 5-card combination (assuming best 5-card poker hand)
    best_hand = list(max(itertools.combinations(combined_hands, 5), key=calculate_score))
    # Convert best_hand to string format
    return best_hand

def calculate_score_without_joker(rank_counts, hand):
    def is_flush(hand):
        suit = hand[0][0]
        return all(card[0] == suit for card in hand if card not in ['BJ', 'RJ'])

    def is_straight(hand):
        rank_indices = sorted([ranks.index(card[1:]) for card in hand if card not in ['BJ', 'RJ']])
        for i in range(len(rank_indices) - 1):
            if rank_indices[i + 1] - rank_indices[i] != 1:
                return False
        return True

    def is_straight_flush(hand):
        return is_straight(hand) and is_flush(hand)

    def is_royal_flush(hand):
        return is_straight_flush(hand) and set(card[1:] for card in hand if card not in ['BJ', 'RJ']) == {'T', 'J', 'Q', 'K', 'A'}

    score = 0

    if is_royal_flush(hand):
        score = 20
    elif is_straight_flush(hand):
        score = 15
    elif max(rank_counts.values()) == 4:
        score = 12
    elif sorted(rank_counts.values())[-2:] == [2, 3]:
        score = 9
    elif is_flush(hand):
        score = 7
    elif is_straight(hand):
        score = 5
    elif max(rank_counts.values()) == 3:
        score = 4
    elif list(rank_counts.values()).count(2) == 2:
        score = 3
    elif 2 in rank_counts.values():
        score = 2
    else:
        score = 1

    return score

def calculate_reward(current_game_id):
    # 获取当前游戏的得分和奖池金额
    scores_key = f"{current_game_id}_SCORES"
    pool_key = f"{current_game_id}_POOL"
    player_scores = redis_client.zrevrange(scores_key, 0, -1, withscores=True)  # 使用 zrevrange 获取从高到低的分数
    prize_pool = int(redis_client.get(pool_key) or 0)

    if not player_scores:
        return {}

    num_players = len(player_scores)
    top_10_percent_index = math.floor(num_players * 0.1)
    top_25_percent_index = math.floor(num_players * 0.25)

    rewards = {}

    # 奖池中的50%奖励前10%的玩家
    top_10_percent_reward = prize_pool * 0.5 / top_10_percent_index if top_10_percent_index > 0 else 0

    # 奖池中35%的奖励前10%-25%的玩家
    top_10_to_25_percent_reward = prize_pool * 0.35 / (top_25_percent_index - top_10_percent_index) if top_25_percent_index > top_10_percent_index else 0

    for i, (player, score) in enumerate(player_scores):
        player = player.decode('utf-8')
        if i < top_10_percent_index:
            rewards[player] = top_10_percent_reward
        elif i < top_25_percent_index:
            rewards[player] = top_10_to_25_percent_reward
        else:
            rewards[player] = 0

    return rewards
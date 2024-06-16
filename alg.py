import hashlib
import hmac
import json
import random
import itertools
import math
from typing import Union
from urllib.parse import unquote
from database import redis_client
from dotenv import load_dotenv
import string
import os

load_dotenv()

# 定义扑克牌，包括大小王
suits = ['H', 'S', 'D', 'C']  # 红桃, 黑桃, 方块, 梅花
ranks = ['2', '3', '4', '5', '6', '7', '8', '9', 'T', 'J', 'Q', 'K', 'A']
jokers = ['BJ', 'RJ']  # 大小王，BJ: Black Joker, RJ: Red Joker

# Constants
PRIME1 = int(os.getenv('PRIME1'))
PRIME2 = int(os.getenv('PRIME2'))
SALT = int(os.getenv('SALT'))
ALPHANUMERIC_SET = string.ascii_letters + string.digits  # 62 characters

def generate_hand(poker_num):
    deck = [suit + rank for suit in suits for rank in ranks] + jokers
    random.shuffle(deck)
    return deck[:poker_num]

def dealer_draw():
    return generate_hand(5)

def calculate_score(hand):
    joker_ranks = ranks + ['BJ', 'RJ']

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
        # Generate all unique combinations of replacements for jokers
        unique_replacements = set(itertools.combinations_with_replacement(ranks, joker_count))
        for replacements in unique_replacements:
            new_hand = replace_jokers(hand, replacements)
            rank_counts, _ = get_rank_counts(new_hand)
            possible_scores.append(calculate_score_without_joker(rank_counts, new_hand))
    else:
        possible_scores.append(calculate_score_without_joker(rank_counts, hand))

    return max(possible_scores)

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

    if is_royal_flush(hand):
        buttom, multiplier = redis_client.hmget("settlement:101", "buttom", "mul")
    elif is_straight_flush(hand):
        buttom, multiplier = redis_client.hmget("settlement:102", "buttom", "mul")
    elif max(rank_counts.values()) == 4:
        buttom, multiplier = redis_client.hmget("settlement:103", "buttom", "mul")
    elif sorted(rank_counts.values())[-2:] == [2, 3]:
        buttom, multiplier = redis_client.hmget("settlement:104", "buttom", "mul")
    elif is_flush(hand):
        buttom, multiplier = redis_client.hmget("settlement:105", "buttom", "mul")
    elif is_straight(hand):
        buttom, multiplier = redis_client.hmget("settlement:106", "buttom", "mul")
    elif max(rank_counts.values()) == 3:
        buttom, multiplier = redis_client.hmget("settlement:107", "buttom", "mul")
    elif list(rank_counts.values()).count(2) == 2:
        buttom, multiplier = redis_client.hmget("settlement:108", "buttom", "mul")
    elif 2 in rank_counts.values():
        buttom, multiplier = redis_client.hmget("settlement:109", "buttom", "mul")
    else:
        buttom, multiplier = redis_client.hmget("settlement:110", "buttom", "mul")
    # Convert bytes to integers
    buttom = float(buttom)
    multiplier = float(multiplier)

    return buttom * multiplier

def combine_hands(dealer_hand, player_hand):
    # Convert string representations of hands into lists
    dealer_hand_list = eval(dealer_hand)
    player_hand_list = eval(player_hand)
    
    # Combine dealer's hand with player's hand
    combined_hands = dealer_hand_list + player_hand_list
    
    # Find the best 5-card combination (assuming best 5-card poker hand)
    best_hand = list(max(itertools.combinations(combined_hands, 5), key=calculate_score))
    # Convert best_hand to string format
    return best_hand

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

def calculate_reward_simplified(current_game_id):
    # 获取当前游戏的得分和奖池金额
    scores_key = f"{current_game_id}_SCORES"
    pool_key = f"{current_game_id}_POOL"
    player_scores = redis_client.zrevrange(scores_key, 0, -1, withscores=True)  # 使用 zrevrange 获取从高到低的分数
    prize_pool = int(redis_client.get(pool_key) or 0)

    if not player_scores:
        return []

    num_players = len(player_scores)
    top_10_percent_index = math.floor(num_players * 0.1)
    top_25_percent_index = math.floor(num_players * 0.25)

    rewards = []

    # 奖池中的50%奖励前10%的玩家
    top_10_percent_reward = prize_pool * 0.5 / top_10_percent_index if top_10_percent_index > 0 else 0

    # 奖池中35%的奖励前10%-25%的玩家
    top_10_to_25_percent_reward = prize_pool * 0.35 / (top_25_percent_index - top_10_percent_index) if top_25_percent_index > top_10_percent_index else 0

    rewards_summary = [
        {"players": top_10_percent_index, "reward_each": top_10_percent_reward},
        {"players": top_25_percent_index, "reward_each": top_10_to_25_percent_reward}
    ]

    return rewards_summary

def check_for_specific_card(hand, card_to_check):
    """
    Check if a hand contains a specific card.
    
    Args:
    hand (str): The hand of the player as a string of cards.
    card_to_check (str): The card to check for in the hand.
    
    Returns:
    bool: True if the hand contains the specified card, False otherwise.
    """
    # Split the hand string into individual cards
    cards = hand.split()
    
    # Check each card in the hand to see if it matches the card to check
    for card in cards:
        if card == card_to_check:
            return True
    return False

def check_for_suit(hand, suit):
    """
    Check if a hand contains any card of a specific suit.
    
    Args:
    hand (str): The hand of the player as a string of cards.
    suit (str): The suit to check for in the hand.
    
    Returns:
    bool: True if the hand contains at least one card of the specified suit, False otherwise.
    """
    # Split the hand string into individual cards
    cards = hand.split()
    
    # Check if any card in the hand matches the specified suit
    for card in cards:
        if card[0] == suit:
            return True
    return False

def get_inv_code_by_uid(uid, length):
    # Amplify and salt the UID
    uid = uid * PRIME1 + SALT

    code = []
    sl_idx = [0] * length

    # Diffusion
    for i in range(length):
        sl_idx[i] = uid % len(ALPHANUMERIC_SET)
        sl_idx[i] = (sl_idx[i] + i * sl_idx[0]) % len(ALPHANUMERIC_SET)
        uid = uid // len(ALPHANUMERIC_SET)

    # Confusion
    for i in range(length):
        idx = (i * PRIME2) % length
        code.append(ALPHANUMERIC_SET[sl_idx[idx]])

    return ''.join(code)

def get_uid_by_inv_code(inv_code):
    length = len(inv_code)
    inv_code_indices = [ALPHANUMERIC_SET.index(char) for char in inv_code]
    
    # Reverse the confusion
    sl_idx = [0] * length
    for i in range(length):
        idx = (i * PRIME2) % length
        sl_idx[idx] = inv_code_indices[i]
    
    # Reverse the diffusion
    uid = 0
    for i in range(length - 1, -1, -1):
        sl_idx[i] = (sl_idx[i] - i * sl_idx[0]) % len(ALPHANUMERIC_SET)
        uid = uid * len(ALPHANUMERIC_SET) + sl_idx[i]

    # Remove the salt and amplify
    uid = (uid - SALT) // PRIME1

    return uid

def prepare_data_to_check(init_data: Union[str, dict]) -> dict:
    if isinstance(init_data, str):
        data_parts = dict(item.split('=') for item in init_data.split('&'))
    elif isinstance(init_data, dict):
        data_parts = init_data
    else:
        raise ValueError("init_data must be either a str or dict")

    if 'user' in data_parts and isinstance(data_parts['user'], str):
        try:
            data_parts['user'] = json.loads(data_parts['user'])
        except json.JSONDecodeError:
            raise ValueError("Invalid JSON format in 'user' field")
    return data_parts

def check_login_method(data_parts):
    # 检查是否存在'user'字段且'user'字段是一个字典，同时存在'hash'字段
    if 'user' in data_parts and isinstance(data_parts['user'], dict) and 'id' in data_parts['user'] and 'hash' in data_parts:
        return 1  # 类型 1
    # 检查是否同时存在'player_name'和'msg_id'字段
    elif 'player_name' in data_parts and 'msg_id' in data_parts:
        return 2  # 类型 2
    # 如果上述条件都不满足，返回类型 0
    return 0  # 类型 0

    
def check_hash(init_data: Union[str, dict], tg_token: str) -> bool:
    data_to_check = prepare_data_to_check(init_data)
    received_hash = data_to_check.get('hash')
    secret_key = hmac.new(tg_token.encode(), "WebAppData".encode(), digestmod=hashlib.sha256).digest()
    data_check_string = '\n'.join(f"{key}={value}" for key, value in sorted(data_to_check.items()) if key != 'hash').encode()
    hash_check = hmac.new(secret_key, data_check_string, digestmod=hashlib.sha256).hexdigest()
    return hash_check == received_hash

def validate(hash_str, init_data, token, c_str="WebAppData"):
    """
    Validates the data received from the Telegram web app, using the
    method documented here: 
    https://core.telegram.org/bots/webapps#validating-data-received-via-the-web-app

    hash_str - the has string passed by the webapp
    init_data - the query string passed by the webapp
    token - Telegram bot's token
    c_str - constant string (default = "WebAppData")
    """

    init_data = sorted([ chunk.split("=") 
          for chunk in unquote(init_data).split("&") 
            if chunk[:len("hash=")]!="hash="],
        key=lambda x: x[0])
    init_data = "\n".join([f"{rec[0]}={rec[1]}" for rec in init_data])

    secret_key = hmac.new(c_str.encode(), token.encode(),
        hashlib.sha256 ).digest()
    data_check = hmac.new( secret_key, init_data.encode(),
        hashlib.sha256)

    return data_check.hexdigest() == hash_str
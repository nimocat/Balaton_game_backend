import random
import itertools

def card_name(number):
    suits = ['Clubs', 'Diamonds', 'Hearts', 'Spades']
    ranks = ['2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K', 'A']
    jokers = ['Red Joker', 'Black Joker']
    
    if number == 53:
        return jokers[0]
    elif number == 54:
        return jokers[1]
    else:
        suit = suits[(number - 1) // 13]
        rank = ranks[(number - 1) % 13]
        return f'{rank} of {suit}'

def random_pick(n):
    if n < 1 or n > 54:
        raise ValueError("N must be between 1 and 54")
    
    numbers = random.sample(range(1, 55), n)
    cards = [card_name(number) for number in numbers]
    
    return cards

def calculate_score(hand):
    suits = ['Clubs', 'Diamonds', 'Hearts', 'Spades']
    ranks = ['2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K', 'A']
    joker_ranks = ranks + ['Joker']

    def is_flush(hand):
        suit = hand[0].split()[-1]
        return all(card.split()[-1] == suit for card in hand)

    def is_straight(hand):
        rank_indices = [joker_ranks.index(card.split()[0]) for card in hand]
        rank_indices.sort()
        for i in range(len(rank_indices) - 1):
            if rank_indices[i + 1] - rank_indices[i] != 1:
                return False
        return True

    def is_straight_flush(hand):
        return is_straight(hand) and is_flush(hand)

    def is_royal_flush(hand):
        return is_straight_flush(hand) and set(card.split()[0] for card in hand) == {'10', 'J', 'Q', 'K', 'A'}

    def get_rank_counts(hand):
        hand_ranks = [card.split()[0] for card in hand if 'Joker' not in card]
        rank_counts = {rank: hand_ranks.count(rank) for rank in ranks}
        joker_count = sum('Joker' in card for card in hand)
        return rank_counts, joker_count

    rank_counts, joker_count = get_rank_counts(hand)
    possible_scores = []

    if joker_count > 0:
        for replacements in itertools.product(ranks, repeat=joker_count):
            new_hand = replace_jokers(hand, replacements)
            rank_counts, _ = get_rank_counts(new_hand)
            possible_scores.append(calculate_score_without_joker(rank_counts, new_hand))
    else:
        possible_scores.append(calculate_score_without_joker(rank_counts, hand))

    return max(possible_scores)

def calculate_score_without_joker(rank_counts, hand):
    suits = ['Clubs', 'Diamonds', 'Hearts', 'Spades']
    ranks = ['2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K', 'A']

    def is_flush(hand):
        suit = hand[0].split()[-1]
        return all(card.split()[-1] == suit for card in hand)

    def is_straight(hand):
        rank_indices = [ranks.index(card.split()[0]) for card in hand if 'Joker' not in card]
        rank_indices.sort()
        for i in range(len(rank_indices) - 1):
            if rank_indices[i + 1] - rank_indices[i] != 1:
                return False
        return True

    def is_straight_flush(hand):
        return is_straight(hand) and is_flush(hand)

    def is_royal_flush(hand):
        return is_straight_flush(hand) and set(card.split()[0] for card in hand) == {'10', 'J', 'Q', 'K', 'A'}

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

def dealer_draw():
    return random_pick(5)

def calculate_reward(score):
    # 简单的奖励计算逻辑，可根据实际情况调整
    return score
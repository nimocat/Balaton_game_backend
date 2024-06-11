import numpy as np
import itertools
import pytest

suits = ['H', 'S', 'D', 'C']  # 红桃, 黑桃, 方块, 梅花
ranks = ['2', '3', '4', '5', '6', '7', '8', '9', 'T', 'J', 'Q', 'K', 'A']
jokers = ['BJ', 'RJ']  # 大小王，BJ: Black Joker, RJ: Red Joker

joker_ranks = ranks + ['BJ', 'RJ']

def is_flush(hands):
    # Extract the first character of each card (the suit)
    suits = np.array([[card[0] for card in hand] for hand in hands])
    return np.all(suits == suits[:, 0][:, np.newaxis], axis=1)

def is_straight(hands):
    rank_indices = np.array([[joker_ranks.index(card[1:]) for card in hand] for hand in hands])
    sorted_indices = np.sort(rank_indices, axis=1)
    differences = np.diff(sorted_indices, axis=1)
    return np.all(differences == 1, axis=1)

def is_straight_flush(hands):
    return is_straight(hands) & is_flush(hands)

def is_royal_flush(hands):
    hand_ranks = np.array([[card[1:] for card in hand] for hand in hands])
    return is_straight_flush(hands) & np.all(np.isin(hand_ranks, ['T', 'J', 'Q', 'K', 'A']), axis=1)

def calculate_scores(hands):
    hands_array = np.array([hand.split() for hand in hands])

    flushes = is_flush(hands_array)
    straights = is_straight(hands_array)
    straight_flushes = is_straight_flush(hands_array)
    royal_flushes = is_royal_flush(hands_array)

    scores = np.zeros(len(hands))
    scores[royal_flushes] = 100
    scores[straight_flushes & ~royal_flushes] = 75
    scores[flushes & ~straight_flushes] = 50
    scores[straights & ~flushes] = 25

    return scores

def generate_random_hands(num_hands, hand_size=5):
    deck = [suit + rank for suit in suits for rank in ranks] + jokers
    np.random.seed(42)  # For reproducibility
    return [' '.join(np.random.choice(deck, hand_size, replace=False)) for _ in range(num_hands)]

@pytest.fixture
def random_hands():
    return generate_random_hands(10000)

def test_calculate_scores_performance(benchmark, random_hands):
    result = benchmark(calculate_scores, random_hands)
    assert len(result) == 10000

if __name__ == "__main__":
    pytest.main()

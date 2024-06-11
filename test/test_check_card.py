import numpy as np
import pytest

def check_for_specific_card_np(hands, card_to_check):
    """
    Check if multiple hands contain a specific card using NumPy.
    
    Args:
    hands (list of str): List of hands, each hand is a string of cards.
    card_to_check (str): The card to check for in the hands.
    
    Returns:
    np.ndarray: Boolean array where True indicates the hand contains the specified card.
    """
    # Split each hand into individual cards and create a 2D NumPy array
    hands_array = np.array([hand.split() for hand in hands])
    
    # Check if each card in the hands matches the card to check
    contains_card = np.any(hands_array == card_to_check, axis=1)
    
    return contains_card

def generate_random_hands(num_hands, hand_size=5):
    suits = ['H', 'S', 'D', 'C']
    ranks = ['2', '3', '4', '5', '6', '7', '8', '9', 'T', 'J', 'Q', 'K', 'A']
    jokers = ['BJ', 'RJ']
    deck = [suit + rank for suit in suits for rank in ranks] + jokers

    np.random.seed(42)  # For reproducibility
    return [' '.join(np.random.choice(deck, hand_size, replace=False)) for _ in range(num_hands)]

@pytest.fixture
def random_hands():
    return generate_random_hands(1000)

def test_check_for_specific_card_performance(benchmark, random_hands):
    card_to_check = "HT"
    
    # Benchmark the performance of check_for_specific_card_np
    result = benchmark(check_for_specific_card_np, random_hands, card_to_check)
    
    assert len(result) == 1000
    assert isinstance(result, np.ndarray)

if __name__ == "__main__":
    pytest.main()
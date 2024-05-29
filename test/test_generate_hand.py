import unittest
from alg import generate_hand
import sys
import os

# Ensure the directory containing alg.py is in the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

class TestGenerateHand(unittest.TestCase):
    def test_generate_hand_length(self):
        poker_num = 5
        hand = generate_hand(poker_num)
        self.assertEqual(len(hand), poker_num)

    def test_generate_hand_unique(self):
        poker_num = 5
        hand = generate_hand(poker_num)
        self.assertEqual(len(hand), len(set(hand)))

    def test_generate_hand_valid_cards(self):
        poker_num = 5
        hand = generate_hand(poker_num)
        suits = ['H', 'S', 'D', 'C']
        ranks = ['2', '3', '4', '5', '6', '7', '8', '9', 'T', 'J', 'Q', 'K', 'A']
        jokers = ['BJ', 'RJ']
        valid_cards = [suit + rank for suit in suits for rank in ranks] + jokers
        for card in hand:
            self.assertIn(card, valid_cards)

    def test_generate_hand_full_deck(self):
        suits = ['H', 'S', 'D', 'C']
        ranks = ['2', '3', '4', '5', '6', '7', '8', '9', 'T', 'J', 'Q', 'K', 'A']
        jokers = ['BJ', 'RJ']
        deck_size = len(suits) * len(ranks) + len(jokers)
        poker_num = deck_size
        hand = generate_hand(poker_num)
        self.assertEqual(len(hand), poker_num)
        self.assertEqual(len(set(hand)), poker_num)

if __name__ == '__main__':
    unittest.main()

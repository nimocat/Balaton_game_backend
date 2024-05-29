import unittest
from alg import calculate_score, calculate_score_without_joker
import sys
import os

# Ensure the directory containing alg.py is in the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


class TestPokerHandScore(unittest.TestCase):

    def test_royal_flush(self):
        hand = ['HT', 'HJ', 'HQ', 'HK', 'HA']
        self.assertEqual(calculate_score(hand), 20)

    def test_straight_flush(self):
        hand = ['H9', 'H8', 'H7', 'H6', 'H5']
        self.assertEqual(calculate_score(hand), 15)

    def test_four_of_a_kind(self):
        hand = ['H9', 'S9', 'D9', 'C9', 'HA']
        self.assertEqual(calculate_score(hand), 12)

    def test_full_house(self):
        hand = ['H9', 'S9', 'D9', 'C8', 'H8']
        self.assertEqual(calculate_score(hand), 9)

    def test_flush(self):
        hand = ['H2', 'H5', 'H7', 'H9', 'HJ']
        self.assertEqual(calculate_score(hand), 7)

    def test_straight(self):
        hand = ['H5', 'S4', 'D3', 'C2', 'HA']
        self.assertEqual(calculate_score(hand), 5)

    def test_three_of_a_kind(self):
        hand = ['H9', 'S9', 'D9', 'C8', 'HA']
        self.assertEqual(calculate_score(hand), 4)

    def test_two_pair(self):
        hand = ['H9', 'S9', 'D8', 'C8', 'HA']
        self.assertEqual(calculate_score(hand), 3)

    def test_one_pair(self):
        hand = ['H9', 'S9', 'D7', 'C8', 'HA']
        self.assertEqual(calculate_score(hand), 2)

    def test_high_card(self):
        hand = ['H2', 'S5', 'D7', 'C9', 'HA']
        self.assertEqual(calculate_score(hand), 1)

    def test_joker_in_hand(self):
        hand = ['BJ', 'HJ', 'HQ', 'HK', 'HA']
        self.assertEqual(calculate_score(hand), 20)  # Joker replaced to complete Royal Flush

    def test_two_jokers_in_hand(self):
        hand = ['BJ', 'RJ', 'HQ', 'HK', 'HA']
        self.assertEqual(calculate_score(hand), 20)  # Both Jokers replaced to complete Royal Flush

if __name__ == '__main__':
    unittest.main()

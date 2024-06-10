import unittest
from alg import calculate_score
import sys
import os

# 将项目根目录添加到sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


class TestCalculateScore(unittest.TestCase):
    def test_is_royal_flush(self):
        hand = ['HJ', 'HQ', 'HK', 'HA', 'HT']
        self.assertEqual(calculate_score(hand), 20, "Should be a Royal Flush with score 80")

    def test_is_straight_flush(self):
        hand = ['H9', 'HJ', 'HQ', 'HK', 'HT']
        self.assertEqual(calculate_score(hand), 15, "Should be a Straight Flush with score 15")

    def test_is_four_of_a_kind(self):
        hand = ['H9', 'D9', 'S9', 'C9', 'HT']
        self.assertEqual(calculate_score(hand), 12, "Should be Four of a Kind with score 12")

    def test_is_full_house(self):
        hand = ['H9', 'D9', 'S9', 'HT', 'DT']
        self.assertEqual(calculate_score(hand), 9, "Should be a Full House with score 9")

    def test_is_flush(self):
        hand = ['H2', 'H4', 'H6', 'H8', 'HJ']
        self.assertEqual(calculate_score(hand), 7, "Should be a Flush with score 7")

    def test_is_straight(self):
        hand = ['H9', 'DJ', 'SQ', 'HK', 'CT']
        self.assertEqual(calculate_score(hand), 5, "Should be a Straight with score 5")

    def test_is_three_of_a_kind(self):
        hand = ['H9', 'D9', 'S9', 'H3', 'HT']
        self.assertEqual(calculate_score(hand), 4, "Should be Three of a Kind with score 4")

    def test_is_two_pair(self):
        hand = ['H9', 'D9', 'HT', 'DT', 'S2']
        self.assertEqual(calculate_score(hand), 3, "Should be Two Pair with score 3")

    def test_is_one_pair(self):
        hand = ['H9', 'D9', 'H3', 'H4', 'H5']
        self.assertEqual(calculate_score(hand), 2, "Should be One Pair with score 2")

    def test_is_high_card(self):
        hand = ['H9', 'D8', 'H3', 'H4', 'H5']
        self.assertEqual(calculate_score(hand), 1, "Should be High Card with score 1")

class TestCalculateScoreWithJokers(unittest.TestCase):
    def test_is_royal_flush_with_jokers(self):
        hand = ['HJ', 'HQ', 'HK', 'BJ', 'RJ']  # BJ and RJ represent Black Joker and Red Joker respectively
        self.assertEqual(calculate_score(hand), 20, "Should be a Royal Flush with score 20 using jokers")

    def test_is_straight_flush_with_jokers(self):
        hand = ['H9', 'BJ', 'HQ', 'HK', 'HT']
        self.assertEqual(calculate_score(hand), 15, "Should be a Straight Flush with score 15 using jokers")

    def test_is_four_of_a_kind_with_jokers(self):
        hand = ['H9', 'D9', 'BJ', 'RJ', 'HT']
        self.assertEqual(calculate_score(hand), 12, "Should be Four of a Kind with score 12 using jokers")

    def test_is_full_house_with_jokers(self):
        hand = ['H9', 'D9', 'BJ', 'HT', 'DT']
        self.assertEqual(calculate_score(hand), 9, "Should be a Full House with score 9 using jokers")

    def test_is_flush_with_jokers(self):
        hand = ['H2', 'H4', 'H6', 'BJ', 'HJ']
        self.assertEqual(calculate_score(hand), 7, "Should be a Flush with score 7 using jokers")

    def test_is_straight_with_jokers(self):
        hand = ['BJ', 'DJ', 'SQ', 'HK', 'CT']
        self.assertEqual(calculate_score(hand), 5, "Should be a Straight with score 5 using jokers")

    def test_is_three_of_a_kind_with_jokers(self):
        hand = ['H9', 'D9', 'BJ', 'H3', 'HT']
        self.assertEqual(calculate_score(hand), 4, "Should be Three of a Kind with score 4 using jokers")

class TestCalculateScoreWithJokers(unittest.TestCase):
    def test_various_hands_with_jokers(self):
        hands_with_scores = [
            (['HJ', 'HQ', 'HK', 'BJ', 'RJ'], 20),  # Royal Flush with jokers
            (['H9', 'BJ', 'HQ', 'HK', 'HT'], 15),  # Straight Flush with jokers
            (['H9', 'D9', 'BJ', 'RJ', 'HT'], 12),  # Four of a Kind with jokers
            (['H9', 'D9', 'BJ', 'HT', 'DT'], 9),   # Full House with jokers
            (['H2', 'H4', 'H6', 'BJ', 'HJ'], 7),   # Flush with jokers
            (['BJ', 'DJ', 'SQ', 'HK', 'CT'], 5),   # Straight with jokers
            (['H9', 'D9', 'BJ', 'H3', 'HT'], 4),   # Three of a Kind with jokers
            (['H9', 'D9', 'HT', 'DT', 'BJ'], 9),   # Full House with jokers (Two pairs upgraded by joker)
            (['H9', 'D9', 'BJ', 'H4', 'H5'], 4),   # Three of a Kind with jokers (One pair upgraded by joker)
            (['H9', 'D8', 'BJ', 'H4', 'H5'], 2)    # High Card with jokers (no upgrade possible)
        ]
        for hand, expected_score in hands_with_scores:
            with self.subTest(hand=hand):
                self.assertEqual(calculate_score(hand), expected_score, f"Should score {expected_score} with hand {hand}")

if __name__ == '__main__':
    unittest.main()
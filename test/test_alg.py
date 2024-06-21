import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from dotenv import load_dotenv

import unittest
from alg import calculate_score, combine_hands, validate
from urllib.parse import unquote
import hmac
import hashlib

# 将项目根目录添加到sys.path
load_dotenv()


class TestCalculateScore(unittest.TestCase):
    def test_is_royal_flush(self):
        hand = ['HJ', 'HQ', 'HK', 'HA', 'HT']
        self.assertEqual(calculate_score(hand), 2400, "Should be a Royal Flush with score 80")

    def test_is_straight_flush(self):
        hand = ['H9', 'HJ', 'HQ', 'HK', 'HT']
        self.assertEqual(calculate_score(hand), 800, "Should be a Straight Flush with score 15")

    def test_is_four_of_a_kind(self):
        hand = ['H9', 'D9', 'S9', 'C9', 'HT']
        self.assertEqual(calculate_score(hand), 420, "Should be Four of a Kind with score 12")

    def test_is_full_house(self):
        hand = ['H9', 'D9', 'S9', 'HT', 'DT']
        self.assertEqual(calculate_score(hand), 160, "Should be a Full House with score 9")

    def test_is_flush(self):
        hand = ['H2', 'H4', 'H6', 'H8', 'HJ']
        self.assertEqual(calculate_score(hand), 140, "Should be a Flush with score 7")

    def test_is_straight(self):
        hand = ['H9', 'DJ', 'SQ', 'HK', 'CT']
        self.assertEqual(calculate_score(hand), 120, "Should be a Straight with score 5")

    def test_is_three_of_a_kind(self):
        hand = ['H9', 'D9', 'S9', 'H3', 'HT']
        self.assertEqual(calculate_score(hand), 90, "Should be Three of a Kind with score 4")

    def test_is_two_pair(self):
        hand = ['H9', 'D9', 'HT', 'DT', 'S2']
        self.assertEqual(calculate_score(hand), 40, "Should be Two Pair with score 3")

    def test_is_one_pair(self):
        hand = ['H9', 'D9', 'H3', 'H4', 'H5']
        self.assertEqual(calculate_score(hand), 20, "Should be One Pair with score 2")

    def test_is_high_card(self):
        hand = ['H9', 'D8', 'H3', 'H4', 'H5']
        self.assertEqual(calculate_score(hand), 5, "Should be High Card with score 1")

class TestCalculateScoreWithJokers(unittest.TestCase):
    def test_is_royal_flush_with_jokers(self):
        hand = ['RJ', 'ST', 'SQ', 'SK', 'SJ']  # BJ and RJ represent Black Joker and Red Joker respectively
        self.assertEqual(calculate_score(hand), 2400, "Should be a Royal Flush with score 20 using jokers")

    # def test_is_straight_flush_with_jokers(self):
    #     hand = ['H9', 'BJ', 'HQ', 'HK', 'HT']
    #     self.assertEqual(calculate_score(hand), 15, "Should be a Straight Flush with score 15 using jokers")

    # def test_is_four_of_a_kind_with_jokers(self):
    #     hand = ['H9', 'D9', 'BJ', 'RJ', 'HT']
    #     self.assertEqual(calculate_score(hand), 12, "Should be Four of a Kind with score 12 using jokers")

    # def test_is_full_house_with_jokers(self):
    #     hand = ['H9', 'D9', 'BJ', 'HT', 'DT']
    #     self.assertEqual(calculate_score(hand), 9, "Should be a Full House with score 9 using jokers")

    # def test_is_flush_with_jokers(self):
    #     hand = ['H2', 'H4', 'H6', 'BJ', 'HJ']
    #     self.assertEqual(calculate_score(hand), 7, "Should be a Flush with score 7 using jokers")

    # def test_is_straight_with_jokers(self):
    #     hand = ['BJ', 'DJ', 'SQ', 'HK', 'CT']
    #     self.assertEqual(calculate_score(hand), 5, "Should be a Straight with score 5 using jokers")

    # def test_is_three_of_a_kind_with_jokers(self):
    #     hand = ['H9', 'D9', 'BJ', 'H3', 'HT']
    #     self.assertEqual(calculate_score(hand), 4, "Should be Three of a Kind with score 4 using jokers")

class TestCalculateScoreWithJokers(unittest.TestCase):
    def test_various_hands_with_jokers(self):
        hands_with_scores = [
            (['HJ', 'HQ', 'HK', 'BJ', 'RJ'], 2400),  # Royal Flush with jokers
            (['H9', 'BJ', 'HQ', 'HK', 'HT'], 800),  # Straight Flush with jokers
            (['H9', 'D9', 'BJ', 'RJ', 'HT'], 420),  # Four of a Kind with jokers
            (['H9', 'D9', 'BJ', 'HT', 'DT'], 160),   # Full House with jokers
            (['H2', 'H4', 'H6', 'BJ', 'HJ'], 140),   # Flush with jokers
            (['BJ', 'DJ', 'SQ', 'HK', 'CT'], 120),   # Straight with jokers
            (['H9', 'D9', 'BJ', 'H3', 'HT'], 90),   # Three of a Kind with jokers
            (['H9', 'D9', 'HT', 'DT', 'BJ'], 160),   # Full House with jokers (Two pairs upgraded by joker)
            (['H9', 'D9', 'BJ', 'H4', 'H5'], 90)   # Three of a Kind with jokers (One pair upgraded by joker)
        ]
        for hand, expected_score in hands_with_scores:
            with self.subTest(hand=hand):
                self.assertEqual(calculate_score(hand), expected_score, f"Should score {expected_score} with hand {hand}")

query_string = "query_id=AAGSxxA5AAAAAJLHEDkHfKui&user=%7B%22id%22%3A957400978%2C%22first_name%22%3A%22Timothy%20Ram.%22%2C%22last_name%22%3A%22%22%2C%22username%22%3A%22timothyramstrong%22%2C%22language_code%22%3A%22zh-hans%22%2C%22allows_write_to_pm%22%3Atrue%7D&auth_date=1718444813&hash=d124e97cf1ddb553ef4ba1ad1e5c3096f1139ca08b680daadb36ca94e3825955"
hash = "d124e97cf1ddb553ef4ba1ad1e5c3096f1139ca08b680daadb36ca94e3825955"

class TestValidateFunction(unittest.TestCase):
    def setUp(self):
        self.token = os.getenv("ACCESS_TOKEN")
        if not self.token:
            raise ValueError("TELEGRAM_BOT_TOKEN must be set in the .env file")

        self.query_string = query_string
        self.correct_hash = hash

    def test_validate_correct_data(self):
        self.assertTrue(validate(self.correct_hash, self.query_string, self.token))

    def test_validate_incorrect_hash(self):
        self.assertFalse(validate("incorrect_hash", self.query_string, self.token))

class TestCombineHand(unittest.TestCase):
    def test_combine_hand(self):
        dealer_hand = str(['RJ', 'ST', 'SQ', 'C5', 'SK'])
        player_hand = str(['SJ', 'HQ', 'S3'])
        combined_hand = combine_hands(dealer_hand, player_hand)
        self.assertEqual(calculate_score(combined_hand), 2400, "The combined hand should score 2400 points")


if __name__ == '__main__':
    unittest.main()
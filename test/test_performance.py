import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


import pytest
from alg import calculate_score, generate_hand

def test_generate_and_score_hand_performance(benchmark):
    # 使用benchmark来测试生成1000副手牌并计算分数的性能
    def generate_and_score():
        hands = [generate_hand(5) for _ in range(10000)]
        scores = [calculate_score(hand) for hand in hands]
        return scores

    result = benchmark(generate_and_score)
    print(f"Generated and scored 1000 hands. {result}")
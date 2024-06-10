import pytest
from alg import calculate_score

@pytest.mark.parametrize("hand, description", [
    (['HJ', 'HQ', 'HK', 'BJ', 'RJ'], "with jokers"),  # 手牌包含大小王
    (['HJ', 'HQ', 'HK', 'HT', 'H9'], "without jokers")  # 手牌不包含大小王
])
def test_calculate_score_performance(benchmark, hand, description):
    # 使用benchmark.fixture来测试函数性能
    result = benchmark(calculate_score, hand)
    print(f"Testing {description}: Score = {result}")
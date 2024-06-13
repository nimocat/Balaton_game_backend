import unittest
import random
import redis
import requests
from time import sleep

class TestPurchase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Start the server

        # Initialize Redis client
        cls.redis_client = redis.StrictRedis(host='localhost', port=6379, db=0)

        # Simulate a player and load 1000 tokens
        cls.player_name = "test_player"
        cls.redis_client.set(f"{cls.player_name}_TOKENS", 1000)  # Assuming money is stored with ID 1

    @classmethod
    def tearDownClass(cls):
        # Clean up Redis data for test_player after tests
        cls.redis_client.delete(f"{cls.player_name}_TOKENS")
        cls.redis_client.delete(f"{cls.player_name}_ITEMS")

    def test_purchase_items(self):
        item_ids = [1001, 1002, 1003]
        for item_id in item_ids:
            purchase_num = random.randint(1, 10)
            response = requests.post(
                "http://localhost:8000/player/purchase",
                json={
                    "player_name": self.player_name,
                    "item_id": item_id,
                    "purchase_num": purchase_num
                }
            )
            self.assertEqual(response.status_code, 200)
            data = response.json()
            self.assertIn("message", data)
            self.assertIn("remaining_balance", data)
            self.assertIn("remaining_stock", data)

            # Check if the Redis result is correct for that user
            player_data = self.redis_client.hgetall(f"{self.player_name}_ITEMS")
            self.assertIn(b'1', player_data)  # Check if balance exists
            self.assertIn(str(item_id).encode('utf-8'), player_data)  # Check if item exists

            # Check if the balance and stock are updated correctly
            remaining_balance = int(player_data[b'1'].decode('utf-8'))
            self.assertEqual(remaining_balance, data["remaining_balance"])

            remaining_stock = int(self.redis_client.hget(f"shop_item:{item_id}", "num").decode('utf-8'))
            self.assertEqual(remaining_stock, data["remaining_stock"])

if __name__ == "__main__":
    unittest.main()


import unittest
import redis
import requests

class TestOpenItems(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Initialize Redis client
        cls.redis_client = redis.StrictRedis(host='localhost', port=6379, db=0)
        cls.player_name = "test_player"
        cls.item_id = "1001"
        cls.item_key = f"item:1001"
        cls.player_key = f"{cls.player_name}_ITEMS"

        # Simulate giving the player an item with item_id = 1001
        cls.redis_client.hset(cls.player_key, cls.item_id, 1)

    @classmethod
    def tearDownClass(cls):
        # Clean up Redis data for test_player after tests
        cls.redis_client.delete(cls.player_key)
        cls.redis_client.delete(cls.item_key)

    def test_open_item(self):
        # Test opening the item
        response = requests.post(
            "http://localhost:8000/items/open_item",
            json={
                "player_name": self.player_name,
                "item_id": self.item_id,
                "item_num": 1
            }
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("message", data)
        self.assertIn("Items opened successfully", data["message"])
        self.assertIn("obtained_items", data)

        # Check if the Redis result is correct for that user
        player_items = self.redis_client.hgetall(self.player_key)
        self.assertIn(str(self.item_id).encode('utf-8'), player_items)  # Check if item exists
        self.assertEqual(int(player_items[str(self.item_id).encode('utf-8')]), 0)  # Check if item count is decremented

        # Additional checks for the obtained items
        for sub_item_id, num in data["obtained_items"].items():
            self.assertIn(str(sub_item_id).encode('utf-8'), player_items)
            self.assertEqual(int(player_items[str(sub_item_id).encode('utf-8')]), num)

if __name__ == "__main__":
    unittest.main()

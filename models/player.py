from datetime import datetime
from beanie import Document, Indexed
from fastapi import logger
from pydantic import BaseModel, Field
from typing import List, Dict, Annotated, Any, Optional
from game_logic import send_rewards
from models.game import Game
from database import redis_client, db
import json

class Player(BaseModel):
    """User register and login auth."""
    player_name: str = Field(..., example="JohnDoe", description="Name of the player logging in")

    @property
    def hands_key(self):
        return f'{Game.current_game}_HANDS'

    @property
    def hand(self):
        return redis_client.hget(Game.hands_key, self.player_name)

    @property
    def longest_checkin(self):
        longest_checkin_key = f"{self.player_name}_LONGEST_CHECKIN"
        data = redis_client.get(longest_checkin_key)
        if data is None:
            data = 0
        else:
            data = int(data)
        return data

    # 确保 player_data 是一个异步方法
    def player_data(self):
        return db.players.find_one({"name": self.player_name})

    def update_hand(self, new_cards: str):
        redis_client.hset(Game.hands_key, self.player_name, json.dumps(new_cards))

    def checked_in(self) -> bool:
        player_data = self.player_data()
        today_checkin = False
        today = datetime.utcnow().date()
        last_checkin_date = player_data.get('last_checkin_date')

        if last_checkin_date:
            last_checkin_date = datetime.strptime(last_checkin_date, '%Y-%m-%d').date()
            if last_checkin_date == today:
                # 如果上次签到是今天，返回已经签到的信息
                today_checkin = True
        return today_checkin
    
    def consecutive_checkins(self) -> int:
        player_data = self.player_data()  # 使用 self.player_data() 获取数据
        if not player_data:
            return 0  # No record found, return 0
        consecutive_checkin_days = player_data.get('consecutive_checkins', 0)
        return consecutive_checkin_days
    
    def fetch_claim_tasks(self, task_type: Optional[int] = None, claim_type: str = "CANCLAIM") -> List[int]:
        """
        Fetches task IDs from CANCLAIM set for a given player that match a specific task type, or all task IDs if no type is specified.
        
        Args:
        player_name (str): The name of the player.
        task_type (Optional[int]): The type of tasks to filter by, or None to fetch all tasks.
        
        Returns:
        List[int]: A list of task IDs that the player can claim, filtered by type if specified.
        """
        # Fetch all task IDs from CANCLAIM
        tasks = redis_client.smembers(f"{self.player_name}_{claim_type}")
        print(f"tasks in {tasks}")
        if task_type is not None:
            # Fetch task IDs of the specified type
            type_tasks = redis_client.smembers(f"task_type:{task_type}")
            # Filter tasks by the specified type
            result = [int(task_id.decode('utf-8')) for task_id in tasks if task_id in type_tasks]
        else:
            # Return all tasks if no type is specified
            result = [int(task_id.decode('utf-8')) for task_id in tasks]
        
        return result

    def claim_task(self, task_id: int) -> bool:
        can_claim_tasks = self.fetch_claim_tasks()
        if int(task_id.encode('utf-8')) not in can_claim_tasks: 
            logger.debug(f"{self.player_name}:claim_task: Task can not be claimed")
            return False
        # Retrieve the task's rewards directly using the task_id from Redis
        task_rewards = redis_client.hget(f"task:{task_id}", "rewards")
        if not task_rewards:
            logger.debug(f"{self.player_name}:claim_task: Task rewards not found for given task ID")
        # Decode and evaluate the rewards string to convert it into a dictionary
        rewards = eval(task_rewards.decode('utf-8'))

        # Use Redis transaction to ensure atomicity
        send_rewards(player_name=self.player_name, task_id=task_id)

        # Update MongoDB with the new items (synchronize Redis to MongoDB)
        self.update_player()
        return rewards
    
    def update_player(self):
        player_tokens_key = f"{self.player_name}_TOKENS"
        player_items_key = f"{self.player_name}_ITEMS"
        player_tokens = redis_client.get(player_tokens_key)
        player_items = redis_client.hgetall(player_items_key)

        update_data = {}
        if player_tokens:
            player_tokens = float(player_tokens.decode('utf-8'))
            update_data["tokens"] = player_tokens

        if player_items:
            player_items = {key.decode('utf-8'): int(value.decode('utf-8')) for key, value in player_items.items()}
            update_data["items"] = player_items

        if update_data:
            db.players.update_one({"name": self.player_name}, {"$set": update_data}, upsert=True)
            print(f"{self.player_name}:update_player: Updated tokens and items in MongoDB")
        else:
            print(f"{self.player_name}:update_player: Nothing to update")

    def make_payment(self, amount):
        player_tokens = redis_client.get(f'{self.player_name}_TOKENS')
        if not player_tokens or float(player_tokens) < amount:
            logger.debug(f'{self.player_name}:make_payment: Insufficient tokens')
        else:
            redis_client.decrby(f'{self.player_name}_TOKENS', amount)
            logger.debug(f'{self.player_name}:make_payment: Payment of {amount} tokens successful')

    def persist_tokens(self):
        player_tokens_key = f"{self.player_name}_TOKENS"
        player_tokens = redis_client.get(player_tokens_key)
        
        if player_tokens:
            # Convert Redis data to float
            player_tokens = float(player_tokens.decode('utf-8'))
            
            # Check if the player exists in MongoDB
            existing_player = self.player_data()
            
            if existing_player:
                # Update existing player's tokens
                db.update_one({"name": self.player_name}, {"$set": {"tokens": player_tokens}})
            else:
                # Insert new player with tokens
                new_player = {"name": self.player_name, "tokens": player_tokens}
                db.players.insert_one(new_player)
class PlayerPayment(Player):
    payment: int = Field(..., example=40, description="Amount paid by the player to enter the game")

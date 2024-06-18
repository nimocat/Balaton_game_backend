from datetime import datetime
from fastapi import logger
from game_logic import send_rewards
from alg import generate_hand
from pydantic import BaseModel, Field
from typing import List, Dict, Optional
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
        self.update_player(player_name=self.player_name)
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
            logger.debug(f"{self.player_name}:update_player: Updated tokens and items in MongoDB")
        else:
            logger.debug(f"{self.player_name}:update_player: Nothing to update")

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

class PlayerInGameResponse(BaseModel):
    cards: str = Field(default=None, example="['AH', 'KH', 'QH', 'JH', '10H']", description="The cards currently held by the player")
    status: int = Field(..., example=1, description="The status of the player in the game (1 for active, 0 for inactive)")

class LoginRequest(BaseModel):
    player_name: str = Field(..., example="JohnDoe", description="Name of the player logging in")

class PlayerResponse(BaseModel):
    game_id: str = Field(..., example="game123", description="Unique identifier for the game")
    score: int = Field(..., example=85, description="Score of the player in the game")
    hand: str = Field(..., example="['AH', 'KH', 'QH', 'JH', '10H']", description="Cards in the player's hand")
    pool: int = Field(..., example=500, description="Current pool amount in the game")

class CurrentGameInfo(BaseModel):
    game_id: str = Field(..., example="game123", description="Unique identifier for the current game")
    pool_amount: int = Field(..., example=1000, description="Total amount in the game's pool")
    player_amount: int = Field(..., example=5, description="Number of players in the game")
    game_time: int = Field(..., example=15, description="Timestamp of the game start")

class FullGameInfo(BaseModel):
    game_id: str = Field(..., example="game123", description="Unique identifier for the game")
    pool_amount: int = Field(..., example=1000, description="Total amount in the game's pool")
    player_amount: int = Field(..., example=5, description="Number of players in the game")
    game_time: str = Field(..., example="20240603170521000000", description="Timestamp of the game start")

class GameInfoRequest(BaseModel):
    game_id: str = Field(None, example="game123", description="Unique identifier for the game")
    player_name: str = Field(..., example="JohnDoe", description="Name of the player requesting game info")

class GameInfoResponse(BaseModel):
    game_id: str = Field(..., example="game123", description="Unique identifier for the game")
    dealer_hand: str = Field(..., example="['SA', 'S7', 'H9', 'CA', 'D8']", 
                                     description="Dealer's 5 cards")
    player_hand: str = Field(..., example="['SJ', 'HT']", 
                                     description="Player's cards")
    player_best_hand: str = Field(..., example="['SA', 'S7', 'H9', 'CA', 'SJ']", 
                                     description="Player's best 5 cards")
    player_score: int = Field(..., example=95, description="Score of the player")
    player_reward: int = Field(..., example=150, description="Reward amount for the player")
    player_rank: int = Field(..., example=1, description="Rank of the player in the game")
    pool_amount: int = Field(..., example=1000, description="Total amount in the game's pool")
    player_count: int = Field(..., example=5, description="Number of players in the game")

class EntranceRequest(BaseModel):
    player_name: str = Field(..., example="JohnDoe", description="Name of the player entering the game")
    payment: int = Field(..., example=50, description="Amount paid by the player to enter the game")

class InviteRequest(BaseModel):
    inviter: str = Field(..., example="JaneDoe", description="Name of the player sending the invite")
    invitee: str = Field(..., example="JohnBone", description="Name of the player being invited")

class PlayerItemsResponse(BaseModel):
    player_name: str = Field(..., example="timothy", 
                                     description="Telegram ID of the player"
)
    items: Dict[str, str] = Field(..., example={"tokens": "20", "super_card": "1"},
                                          description="A dictionary of item names and their corresponding values"
)
    
class GameHistoryEntry(BaseModel):
    game_id: str = Field(..., example="60c72b2f9b7e8b6f4f0e5e13", description="The ID of the game")
    hand: str = Field(..., example="['D5', 'H8', 'C9']", description="The hand of the player")
    score: int = Field(..., example=95, description="The score of the player in the game")
    reward: int = Field(..., example=20, description="The reward earned by the player in the game")
    bet: int = Field(..., example=50, description="The bet placed by the player in the game")

class PlayerReward(BaseModel):
    player_name: str = Field(..., example="player1", description="The name of the player")
    reward: float = Field(..., example=500, description="The total reward the player has received")

class TopDailyRewardsResponse(BaseModel):
    top_players: List[PlayerReward] = Field(
        ...,
        example=[
            {"player_name": "player1", "reward": 500.0},
            {"player_name": "player2", "reward": 450.0},
        ],
        description="A list of the top 100 players and their rewards"
    )

class PlayerHistoryResponse(BaseModel):
    player_name: str = Field(..., example="player1", description="The name of the player")
    history: List[GameHistoryEntry] = Field(
        ...,
        example=[
            {
                "game_id": "60c72b2f9b7e8b6f4f0e5e13",
                "hand": "['S7', 'H2', 'D9']",
                "score": 95,
                "reward": 20,
                "bet": 50
            },
            {
                "game_id": "60c72b2f9b7e8b6f4f0e5e14",
                "hand": "['S7', 'H2', 'D9']",
                "score": 88,
                "reward": 15,
                "bet": 30
            }
        ],
        description="A list of game history entries for the player"
    )

class GameItem(BaseModel):
    item_id: int = Field(..., example=1, description="The ID of the game item")
    type: int = Field(..., example=1, description="The type of the game item")
    name: str = Field(..., example="Sword of Truth", description="The name of the game item")
    short_description: str = Field(..., example="A powerful sword.", description="A short description of the game item")
    long_description: str = Field(..., example="This sword has been wielded by the greatest warriors.", description="A detailed description of the game item")
    available: bool = Field(..., example=True, description="Availability of the game item")

class GameItemsResponse(BaseModel):
    items: List[GameItem] = Field(..., description="A list of all game items")

class ShopItem(BaseModel):
    item_id: int = Field(..., example=1, description="The ID of the shop item")
    price: int = Field(..., example=100, description="The price of the shop item")
    avaliable: bool = Field(..., example=True, description="Availability of the shop item")
    discount: float = Field(..., example=0.1, description="Discount on the shop item")
    num: int = Field(..., example=50, description="Number of items available in the shop")

class ShopItemsResponse(BaseModel):
    items: List[ShopItem] = Field(..., description="A list of all shop items")

class PurchaseRequest(BaseModel):
    player_name: str = Field(..., example="player1", description="The name of the player making the purchase")
    item_id: int = Field(..., example=1, description="The ID of the item to purchase")
    purchase_num: int = Field(..., example=2, description="The number of items to purchase")

class PurchaseResponse(BaseModel):
    message: str = Field(..., example="Purchase completed successfully", description="The result of the purchase operation")
    remaining_balance: int = Field(..., example=500, description="The remaining balance of the player")
    remaining_stock: int = Field(..., example=50, description="The remaining stock of the item")

class OpenItemRequest(BaseModel):
    player_name: str = Field(..., example="player1", description="The name of the player opening the item")
    item_id: str = Field(..., example="1001", description="The ID of the item to open")
    item_num: int = Field(..., example=1, description="The number of items to open")

class OpenItemResponse(BaseModel):
    message: str = Field(..., example="Items opened successfully", description="The result of the operation")
    obtained_items: Dict[int, int] = Field(..., example={2001: 5, 2002: 3}, description="Items obtained from the opened item")

class Type2TaskResponse(BaseModel):
    can_claim: List[int] = Field(..., example=[203])
    claimed: List[int] = Field(..., example=[201, 202])
    progress: int = Field(..., example=2)
    today_checkin: bool = Field(..., example=False, description="Indicates if the player has checked in today")
    consecutive_checkin_days: int = Field(..., example=5, description="The number of consecutive days the player has checked in")

    class Config:
        schema_extra = {
            "example": {
                "can_claim": [203],
                "claimed": [201, 202],
                "progress": 2,
                "today_checkin": False,
                "consecutive_checkin_days": 5
            }
        }

class FarmingResponse(BaseModel):
    status: str = Field(..., description="Indicates if the task is new or existing.")
    message: str = Field(None, description="A message about the task initiation.")
    accumulated_rewards: float = Field(None, description="The total rewards accumulated so far.")
    rewards_per_second: float = Field(None, description="Rate of reward accumulation per second.")
    remaining_time: int = Field(None, description="Time remaining for the task in seconds.")

    class Config:
        schema_extra = {
            "example": {
                "status": "existing",
                "accumulated_rewards": 120.5,
                "rewards_per_second": 0.03347222,
                "remaining_time": 10800,
                "message": "Farming task initiated successfully."
            }
        }

class ReplaceCardIndexRequest(BaseModel):
    index: int = Field(..., description="The index of the card to be replaced in the player's hand")

class PlayerInGameResponse(BaseModel):
    status: bool
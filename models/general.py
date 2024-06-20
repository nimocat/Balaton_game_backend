from datetime import datetime
from fastapi import logger
from game_logic import send_rewards
from alg import generate_hand
from pydantic import BaseModel, Field
from typing import List, Dict, Optional
from database import redis_client, db
import json

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
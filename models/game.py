from alg import generate_hand
from pydantic import BaseModel, Field
from typing import List, Dict, Optional
from beanie import Document

class GameInfo(BaseModel):
    game_id: str = Field(..., example="game123", description="Unique identifier for the current game")
    pool_amount: int = Field(..., example=1000, description="Total amount in the game's pool")
    player_amount: int = Field(..., example=5, description="Number of players in the game")

class GameOut(GameInfo):
    game_time: int = Field(..., example=15, description="Timestamp of the game start")

# class Game(GameOut, Document):

from alg import generate_hand
from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Union
from beanie import Document
from database import redis_client

class GameInfo(BaseModel):
    game_id: str = Field(..., example="game123", description="Unique identifier for the current game")
    # pool_amount: Optional[int] = Field(default=None, example=1000, description="Total amount in the game's pool")
    # player_amount: Optional[int] = Field(default=None, example=5, description="Number of players in the game")
    dealer_hand: Optional[str] = Field(default=None, example="['SA', 'S7', 'H9', 'CA', 'D8']", 
                                     description="Dealer's 5 cards")
    
class PlayerGameInfo(GameInfo):
    player_hand: str = Field(..., example="['SJ', 'HT']", 
                                     description="Player's cards")
    player_best_hand: str = Field(..., example="['SA', 'S7', 'H9', 'CA', 'SJ']", 
                                     description="Player's best 5 cards")
    player_score: int = Field(..., example=95, description="Score of the player")
    player_reward: int = Field(..., example=150, description="Reward amount for the player")
    player_rank: int = Field(..., example=1, description="Rank of the player in the game")

class Game(GameInfo):

    @classmethod
    @property
    def current_remain(cls) -> int:
        return redis_client.ttl("CURRENT_GAME")

    @classmethod
    @property
    def current_game(cls) -> str | None:
        return redis_client.get("CURRENT_GAME")
    
    @classmethod
    @property
    def hands_key(cls) -> str | None:
        return f'{cls.current_game}_HANDS'
    
    @property
    def pool_amount(self) -> int:
        pool_key = f"{self.game_id}_POOL"
        pool_amount = redis_client.get(pool_key)
        print("executing",pool_amount)
        if pool_amount is None:
            pool_amount = 0
        return int(pool_amount)
    
    @property
    def players_amount(self) -> int:
        player_count_key = f"{self.game_id}_COUNT"
        player_amount = redis_client.get(player_count_key)
        if player_amount is None:
            player_amount = 0
        else:
            player_amount = int(player_amount)
        return player_amount

    @property
    def info(self) -> Dict[str, Union[str, int]]:
        """
        Returns the current game information.
        """
        return {
            "game_id": self.game_id,
            "pool_amount": self.pool_amount,  # 确保这里是调用属性
            "player_amount": self.players_amount,
            "game_time": Game.current_remain
        }


    @classmethod
    async def by_id(cls, game_id: str) -> Optional["Game"]:
        """Get a user by email."""
        return await cls.find_one(cls.game_id == game_id)

# class PlayerGame(PlayerGameInfo, Document):
#     @property
#     def remain(self) -> int | None:
#         return redis_client.ttl(self.game_id)
    
#     @@property
#     def pool(self) -> int | None
#     @classmethod
#     async def by_id(cls, game_id: str) -> Optional["Game"]:
#         """Get a user by email."""
#         return await cls.find_one(cls.game_id == game_id)


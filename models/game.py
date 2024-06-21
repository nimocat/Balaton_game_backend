from fastapi import HTTPException
from alg import generate_hand
from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Union
from beanie import Document
from database import redis_client
import asyncio

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

class Game:
    def __init__(self, game_id=None):
        if game_id is None:
            game_id = redis_client.get("CURRENT_GAME").decode('UTF-8')
            if game_id is None:
                raise ValueError("No current game available.")
        self.game_id = game_id

    @property
    def id(self):
        return self.game_id

    @classmethod
    async def current_remain(cls):
        # Assuming this method returns the remaining time for the current game
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
    
    @classmethod
    async def getEndedGameInfo(cls, game_id: str, player_name: str) -> Optional["Game"]:
        """Get a user by email."""
        # 获取荷官手牌
        dealer_key = f"{game_id}_DEALER"
        dealer_hand = redis_client.get(dealer_key)
        if not dealer_hand:
            raise HTTPException(status_code=404, detail="Game ID not found or dealer hand not set")
        dealer_hand = dealer_hand.decode('utf-8')
        print(dealer_hand)

        # 获取玩家手牌
        hands_key = f"{game_id}_HANDS"
        player_hand = redis_client.hget(hands_key, player_name)
        if not player_hand:
            raise HTTPException(status_code=404, detail="Player not found in the specified game")
        player_hand = player_hand.decode('utf-8')

        # 获取玩家得分
        scores_key = f"{game_id}_SCORES"
        player_score = redis_client.zscore(scores_key, player_name)
        if player_score is None:
            raise HTTPException(status_code=404, detail="Player score not found")
        
        # 获取玩家最佳手牌
        best_hands_key = f"{game_id}_BEST_HANDS"
        player_best_hand = redis_client.hget(best_hands_key, player_name)
        if not player_hand:
            raise HTTPException(status_code=404, detail="Player not found in the specified game")
        player_best_hand = player_best_hand.decode('utf-8')

        # 获取玩家奖励
        rewards_key = f"{game_id}_REWARDS"
        player_reward = int(redis_client.zscore(rewards_key, player_name))
        if player_reward is None:
            player_reward = 0  # If no reward found, default to 0

        # 获取玩家排名
        player_rank = redis_client.zrevrank(scores_key, player_name)
        if player_rank is None:
            raise HTTPException(status_code=404, detail="Player rank not found")

        # 获取奖池总金额
        pool_key = f"{game_id}_POOL"
        pool_amount = redis_client.get(pool_key)
        if pool_amount is None:
            pool_amount = 0
        else:
            pool_amount = int(pool_amount)

        # 获取所有玩家人数
        player_count = redis_client.get(f"{game_id}_COUNT")
        if player_count is None:
            player_count = 0
        else:
            player_count = int(player_count)

        # 构造返回的JSON数据
        game_info = GameInfoResponse(
            game_id=game_id,
            dealer_hand=dealer_hand,
            player_hand=player_hand,
            player_best_hand=player_best_hand,  # Assuming best hand is the player's hand itself
            player_score=player_score,
            player_reward=player_reward,
            player_rank=player_rank,
            pool_amount=pool_amount,
            player_count=player_count
        )
        
        return game_info

    @classmethod
    async def currentGameInfo(cls):
        game_id = redis_client.get("CURRENT_GAME")
        if game_id is not None:
            game_id = game_id.decode('utf-8')  # Convert bytes to string
            game = cls(game_id=game_id)
            return {
                "game_id": game.game_id,
                "pool_amount": game.pool_amount,
                "player_amount": game.players_amount,
                "game_time": await cls.current_remain()
            }
        await asyncio.sleep(0.2)  # Wait for 0.5 seconds before retrying

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


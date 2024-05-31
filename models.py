from alg import generate_hand
from pydantic import BaseModel
from typing import List, Dict

class Player:
    def __init__(self, name):
        self.name = name
        self.hand = []
        self.enter_game()

    def enter_game(self):
        self.hand = generate_hand(2)
        print(f"Player {self.name} has entered the game with hand: {self.hand}")

class LoginRequest(BaseModel):
    player_name: str

class PlayerResponse(BaseModel):
    game_id: str
    score: int
    hand: str
    pool: int

class CurrentGameInfo(BaseModel):
    game_id: str
    pool_amount: int
    player_amount: int
    game_time: str

class FullGameInfo(BaseModel):
    game_id: str
    pool_amount: int
    player_amount: int
    game_time: str

class GameInfoRequest(BaseModel):
    game_id: str
    player_name: str

class GameInfoResponse(BaseModel):
    game_id: str
    dealer_hand: List[str]
    player_hand: List[str]
    player_best_hand: List[str]
    player_score: float
    player_reward: float
    player_rank: int
    pool_amount: int
    player_count: int

class EntranceRequest(BaseModel):
    player_name: str
    payment: int
# class Game(BaseModel):
#     game_id: str
#     dealer_hand: list[str] = []
#     players: list[Player] = []
#     start_time: datetime
#     end_time: datetime = None
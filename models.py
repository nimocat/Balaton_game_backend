from alg import generate_hand

class Player:
    def __init__(self, name):
        self.name = name
        self.hand = []
        self.enter_game()

    def enter_game(self):
        self.hand = generate_hand(2)
        print(f"Player {self.name} has entered the game with hand: {self.hand}")

# class Game(BaseModel):
#     game_id: str
#     dealer_hand: list[str] = []
#     players: list[Player] = []
#     start_time: datetime
#     end_time: datetime = None
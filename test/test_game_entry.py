import pytest
import requests

# Define the base URL of your API
BASE_URL = "http://47.254.196.156:8000"

# Test data for multiple players
players = [
    {"username": "player1", "password": "pass1"},
    {"username": "player2", "password": "pass2"},
    {"username": "player3", "password": "pass3"}
]

@pytest.mark.parametrize("player", players)
def test_player_entry(player):
    # Step 1: Player logs in
    login_response = requests.post(f"{BASE_URL}/login", json=player)
    assert login_response.status_code == 200

    # Step 2: Admin adds tokens to the player's account
    admin_token = "admin_secret"  # This should be securely handled in real scenarios
    faucet_response = requests.post(
        f"{BASE_URL}/admin/faucet",
        json={"player_name": player['username']},
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert faucet_response.status_code == 200

    # Step 3: Player enters the game
    game_entry_response = requests.post(f"{BASE_URL}/enter_game", json={"player_name": player['username']})
    assert game_entry_response.status_code == 200

    # Optionally check the response content
    assert "tokens" in faucet_response.json()
    assert faucet_response.json()["tokens"] > 0

# Additional setup for entering the game can be added here
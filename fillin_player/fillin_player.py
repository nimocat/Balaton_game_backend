import csv
import random
import string

def generate_unique_random_player_names(num_names):
    """
    Generate a list of unique random player names.
    
    Args:
    num_names (int): The number of unique random names to generate.
    
    Returns:
    list: A list containing the generated unique random names.
    """
    names = set()
    while len(names) < num_names:
        name_length = random.randint(5, 10)  # Random name length between 5 and 10 characters
        name = ''.join(random.choices(string.ascii_letters, k=name_length))
        names.add(name)
    return list(names)

def save_player_names_to_csv(file_path, names):
    """
    Save a list of names to a CSV file.
    
    Args:
    file_path (str): The path to the CSV file where names will be saved.
    names (list): The list of names to save.
    """
    with open(file_path, mode='w', newline='') as file:
        writer = csv.writer(file)
        for name in names:
            writer.writerow([name])

import requests

def login_and_request_tokens(names):
    """
    For each name in the list, login to the game API and request tokens 100 times.
    
    Args:
    names (list): The list of player names.
    """
    login_url = "https://api.balaton.bet/api/v1/game/user_login"
    token_url = "https://api.balaton.bet/api/v1/admin/faucet"
    
    for name in names:
        # Login request for each user
        login_payload = {"player_name": name}
        login_response = requests.post(login_url, json=login_payload)
        
        if login_response.status_code == 200:
            # Request tokens 100 times for the user
            for _ in range(1):
                token_response = requests.post(token_url, json={"player_name": name})
                if token_response.status_code != 200:
                    print(f"Failed to get tokens for {name}")
        else:
            print(f"Login failed for {name}, print{login_response}")

import threading
import time
import random

def player_entrance(player_name):
    entrance_url = "https://api.balaton.bet/api/v1/game/player_entrance"
    entrance_payload = {"player_name": player_name, "payment": 40}
    response = requests.post(entrance_url, json=entrance_payload)
    if response.status_code == 200:
        print(f"Player {player_name} entered the game successfully.")
    else:
        print(f"Failed to enter game for {player_name}: {response.text}")

def main():
    # Read player names from players.csv
    with open('players.csv', mode='r') as file:
        reader = csv.reader(file)
        player_names = [row[0] for row in reader]

    # Randomly select players and let them enter the game in 10 separate threads
    def entrance_thread():
        while True:
            selected_player = random.choice(player_names)
            player_entrance(selected_player)
            time.sleep(random.uniform(0.5, 2))  # Random sleep to simulate staggered requests

    threads = []
    for _ in range(5):
        t = threading.Thread(target=entrance_thread)
        t.start()
        threads.append(t)

    for t in threads:
        t.join()

if __name__ == "__main__":
    main()


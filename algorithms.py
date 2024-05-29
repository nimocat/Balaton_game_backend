import random

def card_name(number):
    suits = ['Clubs', 'Diamonds', 'Hearts', 'Spades']
    ranks = ['2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K', 'A']
    jokers = ['Red Joker', 'Black Joker']
    
    if number == 53:
        return jokers[0]
    elif number == 54:
        return jokers[1]
    else:
        suit = suits[(number - 1) // 13]
        rank = ranks[(number - 1) % 13]
        return f'{rank} of {suit}'

def random_pick(n):
    if n < 1 or n > 54:
        raise ValueError("N must be between 1 and 54")
    
    numbers = random.sample(range(1, 55), n)
    cards = [card_name(number) for number in numbers]
    
    return cards

def deal_cards(n):
    deck = list(range(1, 55))
    return random.sample(deck, n)

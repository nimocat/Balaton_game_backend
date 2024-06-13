from database import db, redis_client
import datetime

def login_hook(player_name: str):
    update_data = prepare_login_data(player_name)
    update_mongo_data(player_name, update_data)
    # update_daily_task(player_name)

def prepare_login_data(player_name: str):
    player_data = db.players.find_one({"name": player_name})
    current_time = datetime.datetime.utcnow()
    last_login_time = player_data.get('last_login_time') if player_data else None
    
    update_data = {}
    update_data['last_login_time'] = current_time

    if last_login_time is None or (last_login_time and last_login_time.date() < current_time.date()):
        # It's a new day since the last login
        new_total_login_days = player_data.get('total_login_days', 0) + 1 if player_data else 1
        update_data['total_login_days'] = new_total_login_days

    return update_data

def update_mongo_data(player_name: str, update_data: dict):
    db.players.update_one(
        {"name": player_name},
        {"$set": update_data},
        upsert=True
    )

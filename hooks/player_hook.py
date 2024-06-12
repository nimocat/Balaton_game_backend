from database import db, redis_client
import datetime

def login_hook(player_name: str):
    update_last_login_time(player_name)
    # update_daily_task(player_name)

def update_last_login_time(player_name: str):
    player_data = db.players.find_one({"name": player_name})
    current_time = datetime.datetime.utcnow()
    last_login_time = player_data.get('last_login_time') if player_data else None
    
    if last_login_time is None or last_login_time.date() < current_time.date():
        # It's a new day since the last login
        new_total_login_days = player_data.get('total_login_days', 0) + 1 if player_data else 1
        db.players.update_one(
            {"name": player_name},
            {"$set": {"last_login_time": current_time, "total_login_days": new_total_login_days}},
            upsert=True
        )
    else:
        # Update only the last login time
        db.players.update_one(
            {"name": player_name},
            {"$set": {"last_login_time": current_time}},
            upsert=True
        )
    
def update_daily_task(player_name: str):
    if not db.players.find_one({"name": player_name, "daily_tasks.id": 1}):
        db.players.update_one(
            {"name": player_name},
            {"$set": {"daily_tasks": {"id": 1, "key": 1}}},
            upsert=True
        )
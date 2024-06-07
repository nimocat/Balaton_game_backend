from database import db, redis_client
import datetime

def login_hook(player_name: str):
    update_last_login_time(player_name)
    # update_daily_task(player_name)

def update_last_login_time(player_name: str):
    db.players.update_one(
    {"name": player_name},
    {"$set": {"last_login_time": datetime.datetime.utcnow()}},
    upsert=True
)
    
def update_daily_task(player_name: str):
    if not db.players.find_one({"name": player_name, "daily_tasks.id": 1}):
        db.players.update_one(
            {"name": player_name},
            {"$set": {"daily_tasks": {"id": 1, "key": 1}}},
            upsert=True
        )
from fastapi import FastAPI
from game_logic import start_game_threads
from routes import router
from database import db, redis_client
from routers.admin import admin
import sys
import time
from contextlib import asynccontextmanager
import asyncio
from datetime import datetime, timedelta

sys.path.append('routes')
# 每次游戏，记录CURRENT_GAME - str
# CURRENT_GAME_DEALER - str
# CURRENT_GAME_PLAYERS - list
# CURRENT_GAME_SCORES - zset
# CURRENT_GAME_POOL - int
def clear_reward_ranking_day():
    redis_client.delete("REWARD_RANKING_DAY")

def schedule_clear_task():
    while True:
        now = datetime.utcnow()
        next_run = datetime(now.year, now.month, now.day) + timedelta(days=1)
        sleep_time = (next_run - now).total_seconds()
        time.sleep(sleep_time)
        clear_reward_ranking_day()

@asynccontextmanager
async def lifespan(app: FastAPI):
    task = asyncio.create_task(schedule_clear_task())
    try:
        yield
    finally:
        task.cancel()
        await task

app = FastAPI()
app.include_router(router, prefix="/api/v1/game")
app.include_router(admin, prefix="/api/v1/admin")

if __name__ == "__main__":
    start_game_threads()

    # 启动FastAPI应用
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
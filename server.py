from fastapi import FastAPI
from game_logic import start_game_threads
from routes import router
from database import db, redis_client

app = FastAPI()
app.include_router(router)

# 每次游戏，记录CURRENT_GAME - str
# CURRENT_GAME_DEALER - str
# CURRENT_GAME_PLAYERS - list
# CURRENT_GAME_SCORES - zset
# CURRENT_GAME_POOL - int

if __name__ == "__main__":
    start_game_threads()

    # 启动FastAPI应用
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
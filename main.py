from fastapi import FastAPI
from database import db, redis_client
from routers.admin import admin
from routers.items import items
from routers.routes import router
import time
from contextlib import asynccontextmanager
import asyncio
from datetime import datetime, timedelta
from utils.pre_loads import load_data_from_files

# 每次游戏，记录CURRENT_GAME - str
# CURRENT_GAME_DEALER - str
# CURRENT_GAME_PLAYERS - list
# CURRENT_GAME_SCORES - zset
# CURRENT_GAME_POOL - int

app = FastAPI()
app.include_router(router, prefix="/api/v1/game")
app.include_router(admin, prefix="/api/v1/admin")
app.include_router(items, prefix="/api/v1/items")

if __name__ == "__main__":
    # load data from files first
    load_data_from_files()

    # 启动FastAPI应用
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
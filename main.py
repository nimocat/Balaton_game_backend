from fastapi import FastAPI, Request
from database import db, redis_client
from routers.admin import admin
from routers.items import items
from routers.routes import router
import time
from contextlib import asynccontextmanager
import asyncio
from datetime import datetime, timedelta
from utils.pre_loads import load_data_from_files
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
# 每次游戏，记录CURRENT_GAME - str
# CURRENT_GAME_DEALER - str
# CURRENT_GAME_PLAYERS - list
# CURRENT_GAME_SCORES - zset
# CURRENT_GAME_POOL - int

app = FastAPI()
app.include_router(router, prefix="/api/v1/game")
app.include_router(admin, prefix="/api/v1/admin")
app.include_router(items, prefix="/api/v1/items")

templates = Jinja2Templates(directory="templates")

@app.get("/logs", response_class=HTMLResponse)
async def read_logs(request: Request):
    log_file_path = '/home/ecs-user/Balaton_game_backend/balaton.log'
    try:
        with open(log_file_path, 'r') as file:
            lines = file.readlines()
            last_200_lines = lines[-50:]  # Get the last 200 lines
    except FileNotFoundError:
        last_200_lines = ["Log file not found."]
    
    return templates.TemplateResponse("logs.html", {"request": request, "logs": last_200_lines})

if __name__ == "__main__":
    # load data from files first
    load_data_from_files()

    # 启动FastAPI应用
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
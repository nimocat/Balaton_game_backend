from fastapi import FastAPI, Request
from database import db, redis_client
from routers.admin import admin
from routers.items import items
from routers.routes import router
from routers.sockets import game_ws
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from utils.pre_loads import load_data_from_files
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from beanie import init_beanie
# 每次游戏，记录CURRENT_GAME - str
# CURRENT_GAME_DEALER - str
# CURRENT_GAME_PLAYERS - list
# CURRENT_GAME_SCORES - zset
# CURRENT_GAME_POOL - int

@asynccontextmanager
async def lifespan(app: FastAPI):  # type: ignore
    """Initialize application services."""
    await init_beanie(database=db, document_models=["Player"])
    print("Startup complete")
    yield
    print("Shutdown complete")

app = FastAPI()

# Add CORS middleware configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 允许所有源
    allow_credentials=True,
    allow_methods=["*"],  # 允许所有方法
    allow_headers=["*"],  # 允许所有头部
)
app.include_router(router, prefix="/api/v1/game")
app.include_router(admin, prefix="/api/v1/admin")
app.include_router(items, prefix="/api/v1/items")
app.include_router(game_ws)

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
    uvicorn.run("main:app", host="0.0.0.0", port=8000)
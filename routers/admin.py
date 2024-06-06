import pandas as pd
import redis
from fastapi import APIRouter, HTTPException, Depends, FastAPI
from pydantic import BaseModel
from pymongo import MongoClient
from database import redis_client
import logging
import sys
from database import db

admin = APIRouter()
admin_secret = "admin_secret"
tasks_collection = db.tasks

# 配置日志记录
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 函数：管理员接口，通过口令重新加载任务数据到 Redis 中
def admin_auth(token: str):
    # 这里是管理员验证逻辑，假设口令是 "admin_secret"
    if token != admin_secret:
        raise HTTPException(status_code=403, detail="Unauthorized")

@admin.post("/faucet", summary="Admin endpoint to add tokens to a player's account", tags=["admin"])
async def faucet(player_name: str):
    # 检查玩家是否存在于 Redis 中
    player_items_key = f"{player_name}_ITEMS"

    # 增加 1000 个 tokens
    redis_client.hincrby(player_items_key, "1", 1000)
    new_balance = redis_client.hget(player_items_key, "1").decode('utf-8')
    
    logger.info(f"Player {player_name} received 1000 tokens. New balance: {new_balance}")

    return {"player_name": player_name, "new_balance": new_balance}

@admin.post("/item_faucet", summary="Admin endpoint to add items to a player's account", tags=["admin"])
async def faucet(player_name: str, item_id: str):
    # 获得玩家items key
    player_items_key = f"{player_name}_ITEMS"

    item_key = f"item:{item_id}"
    if not redis_client.exists(item_key):
        return {"message": "Item not found", "status": 0}
    # 增加 1000 个 item_id
    redis_client.hincrby(player_items_key, item_id, 100)
    new_balance = redis_client.hget(player_items_key, item_id).decode('utf-8')
    
    logger.info(f"Player {player_name} received 100 {item_id} items. New balance: {new_balance}")

    return {"player_name": player_name, "new_balance": new_balance}

# 函数：将 task.xlsx 文件加载到 Redis 中
def load_tasks_to_redis():
    df = pd.read_excel("../tasks/task.xlsx")
    tasks = df.to_dict(orient='records')

    with redis_client.pipeline() as pipe:
        for task in tasks:
            task_id = task["task_id"]
            pipe.hmset(f"task:{task_id}", task)
        pipe.execute()
    logger.info("Tasks loaded into Redis")

# 函数：将 task.xlsx 文件加载到 MongoDB 中的 tasks 集合
def load_tasks_to_mongodb():
    df = pd.read_excel("task.xlsx")
    tasks = df.to_dict(orient='records')

    # 清空现有的 tasks 集合
    tasks_collection.delete_many({})

    # 将任务数据插入到 tasks 集合中
    tasks_collection.insert_many(tasks)
    logger.info("Tasks loaded into MongoDB")

@admin.post("/reload_tasks")
async def reload_tasks(token: str = Depends(admin_auth)):
    load_tasks_to_mongodb()
    return {"message": "Tasks reloaded into Redis"}
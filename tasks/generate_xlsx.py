import pandas as pd
import redis
from fastapi import APIRouter, HTTPException, Depends, FastAPI
from pydantic import BaseModel
from pymongo import MongoClient
import logging

# 创建示例任务数据并保存为 task.xlsx 文件
tasks = {
    "task_id": [1, 2],
    "name": ["Share with friends", "Daily Share Task"],
    "description": ["Share Balaton to a Telegram group to get 20 tokens", "Share your unique link to multiple groups daily to earn tokens"],
    "reward_tokens": [20, 10],
    "reward_item_id": [101, 102],
    "refresh_time": [24, 24]
}

df = pd.DataFrame(tasks)
df.to_excel("./task.xlsx", index=False)
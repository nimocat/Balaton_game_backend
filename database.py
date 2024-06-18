from fastapi import FastAPI
from pymongo import MongoClient
from bson import ObjectId
from datetime import datetime
import redis
import os
from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient
import os
import pkgutil
import importlib
from beanie import Document, init_beanie
from typing import List, Type

def load_beanie_document_models(models_package: str) -> List[Type[Document]]:
    models = []
    package = importlib.import_module(models_package)
    for loader, module_name, is_pkg in pkgutil.walk_packages(package.__path__, package.__name__ + '.'):
        module = importlib.import_module(module_name)
        for attribute_name in dir(module):
            attribute = getattr(module, attribute_name)
            if isinstance(attribute, type) and issubclass(attribute, Document) and attribute is not Document:
                models.append(attribute)
    return models

load_dotenv()  # Load environment variables from .env file
# Load the MongoDB connection string from the environment variable MONGODB_URI
CONNECTION_STRING = os.getenv('MONGODB_URI')

# Create a MongoDB client
mongo_client = MongoClient(CONNECTION_STRING)
redis_client = redis.Redis(host='localhost', port=6379, db=0, max_connections=50)
db = mongo_client.balaton
# document_models = load_beanie_document_models('your_application.models')
# async def init_db(app: FastAPI):
#     mongo_client = AsyncIOMotorClient(os.getenv('MONGODB_URI'))
#     app.db = mongo_client.balaton
#     app.redis_client = redis.Redis(host='localhost', port=6379, db=0, max_connections=50)
#     document_models = load_beanie_document_models('your_application.models')
#     await init_beanie(database=db, document_models=document_models)
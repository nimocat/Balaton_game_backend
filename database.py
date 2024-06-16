from pymongo import MongoClient
from bson import ObjectId
from datetime import datetime
import redis
import os
from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient

load_dotenv()  # Load environment variables from .env file
# Load the MongoDB connection string from the environment variable MONGODB_URI
CONNECTION_STRING = os.getenv('MONGODB_URI')

# Create a MongoDB client
mongo_client = AsyncIOMotorClient(CONNECTION_STRING)
redis_client = redis.Redis(host='localhost', port=6379, db=0, max_connections=50)

db = mongo_client.balaton
from pymongo import MongoClient
from bson import ObjectId
from datetime import datetime
import redis

mongo_client = MongoClient("mongodb://root:Cradles!3664@dds-3ns97321134989341223-pub.mongodb.rds.aliyuncs.com:3717,dds-3ns97321134989342911-pub.mongodb.rds.aliyuncs.com:3717/admin?replicaSet=mgset-60720061")
redis_client = redis.Redis(host='localhost', port=6379, db=0)

db = mongo_client.balaton

def serialize_objectid(data):
    if isinstance(data, list):
        return [serialize_objectid(item) for item in data]
    elif isinstance(data, dict):
        return {key: serialize_objectid(value) for key, value in data.items()}
    elif isinstance(data, ObjectId):
        return str(data)
    elif isinstance(data, datetime):
        return data.isoformat()
    else:
        return data
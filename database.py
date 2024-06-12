from pymongo import MongoClient
from bson import ObjectId
from datetime import datetime
import redis

mongo_client = MongoClient("mongodb://root:Cradles!3664@dds-3ns97321134989341223-pub.mongodb.rds.aliyuncs.com:3717,dds-3ns97321134989342911-pub.mongodb.rds.aliyuncs.com:3717/admin?replicaSet=mgset-60720061", maxPoolSize = 50, minPoolSize = 10)
redis_client = redis.Redis(host='localhost', port=6379, db=0, max_connections=50)

db = mongo_client.balaton
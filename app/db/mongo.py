from pymongo import MongoClient

from app.core.config import MONGO_URI

# Fail fast when Mongo is down — avoids HTTP clients hanging until read-timeout (~30s).
client = MongoClient(
    MONGO_URI,
    serverSelectionTimeoutMS=5_000,
    connectTimeoutMS=5_000,
    socketTimeoutMS=20_000,
)
db = client["Intellectual_AI"]

chats_collection = db["chats"]

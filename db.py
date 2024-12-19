from pymongo import MongoClient
from bson import ObjectId
from config import Config
import logging

class Database:
    def __init__(self):
        try:
            self.client = MongoClient(Config.MONGO_URI)
            self.db = self.client["stackwalls"]
            self.freelancers_collection = self.db["freelancers"]
            self.users_collection = self.db["users"]
            logging.info("Connected to MongoDB successfully.")
        except Exception as e:
            logging.error(f"Failed to connect to MongoDB: {e}")
            raise e

    def get_freelancer(self, user_id):
        try:
            return self.freelancers_collection.find_one({"user_id": ObjectId(user_id)})
        except Exception as e:
            logging.error(f"Error fetching freelancer: {e}")
            raise e

    def get_user(self, user_id):
        try:
            return self.users_collection.find_one({"_id": ObjectId(user_id)})
        except Exception as e:
            logging.error(f"Error fetching user: {e}")
            raise e

    def close(self):
        self.client.close()
        logging.info("MongoDB connection closed.")
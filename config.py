# config.py
import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    MONGO_URI = os.getenv("MONGO_URI")
    GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
    LOG_LEVEL = os.getenv("LOG_LEVEL", "ERROR")
    # Add other configurations as needed

    @staticmethod
    def validate():
        if not Config.MONGO_URI:
            raise ValueError("MONGO_URI environment variable not set.")
        if not Config.GOOGLE_API_KEY:
            raise ValueError("GOOGLE_API_KEY environment variable not set.")

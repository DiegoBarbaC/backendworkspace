import os
from dotenv import load_dotenv

load_dotenv()

class config:
    MONGO_URI = os.getenv("MONGO_URI")
    JWT_SECRET_KEY = os.getenv("SECRET_KEY")
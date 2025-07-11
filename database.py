from motor.motor_asyncio import AsyncIOMotorClient
from pymongo.collection import Collection
from pymongo.database import Database

from config import MONGO_URI
from schemas.request import Request
from schemas.feedback import Feedback

db_client = AsyncIOMotorClient(MONGO_URI)
db = db_client["studmisto"]


def setup_indexes(db: Database):
    db_requests: Collection[Request] = db.requests
    db_requests.create_index("user_id")

    db_feedback: Collection[Feedback] = db.feedback
    db_feedback.create_index("admin_message_id")
    db_feedback.create_index([("user_id", 1), ("user_message_id", 1)])

from typing import TypedDict


class Feedback(TypedDict):
    user_id: int
    user_message_id: int
    admin_message_id: int

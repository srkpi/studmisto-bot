from datetime import datetime
from typing import Optional, TypedDict


class Request(TypedDict):
    name: str
    phone: str
    dorm: str
    problem_type: str
    details: Optional[str]
    forwarded_message_id: Optional[int]
    status: str
    timestamp: datetime
    edit_timestamp: datetime
    user_id: int
    username: Optional[str]
    full_name: Optional[str]
    set_status_user_id: int

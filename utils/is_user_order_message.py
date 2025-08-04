import re
from aiogram.types import Message


def is_user_order_message(msg: Message):
    return msg.from_user.is_bot and re.search(r"#R\d+", msg.text)

from aiogram.types import Message, CallbackQuery

def get_user_label(call: Message | CallbackQuery) -> str:
    username = call.from_user.username
    if username:
        return f"@{username}"

    first_name = call.from_user.first_name
    last_name = call.from_user.last_name

    return f"{first_name} {last_name}" if last_name else first_name

from aiogram.types import Message
from aiogram.fsm.context import FSMContext


async def delete_last_message(msg: Message, state: FSMContext) -> None:
    data = await state.get_data()

    message_id = data.get("last_message_id")
    if message_id is None:
        return

    try:
        await msg.bot.delete_message(chat_id=msg.chat.id, message_id=message_id)
    except Exception:
        pass

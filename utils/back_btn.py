from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def back_btn(target: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="⬅ Назад", callback_data=f"back:{target}")]
        ]
    )

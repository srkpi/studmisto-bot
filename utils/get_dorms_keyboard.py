from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def get_dorms_keyboard(dorms: list[int]) -> InlineKeyboardMarkup:
    buttons = []
    row = []

    for i, dorm in enumerate(dorms, 1):
        dorm_str = str(dorm)
        row.append(
            InlineKeyboardButton(text=dorm_str, callback_data=f"dorm:{dorm_str}")
        )
        if i % 3 == 0:
            buttons.append(row)
            row = []

    if row:
        buttons.append(row)

    buttons.append([InlineKeyboardButton(text="⬅ Назад", callback_data="back:phone")])

    return InlineKeyboardMarkup(inline_keyboard=buttons)

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from constants.order_statuses import ORDER_STATUS_NAMES, OrderStatus


def get_status_keyboard(
    current_status: OrderStatus, request_id: str
) -> InlineKeyboardMarkup:
    buttons = []
    for status in OrderStatus:
        if status == current_status or status == OrderStatus.CANCELLED:
            continue

        buttons.append(
            [
                InlineKeyboardButton(
                    text=ORDER_STATUS_NAMES[status],
                    callback_data=f"status:{status.name}:{request_id}",
                ),
            ]
        )

    return InlineKeyboardMarkup(inline_keyboard=buttons)

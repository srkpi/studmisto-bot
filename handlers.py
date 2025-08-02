import re
from aiogram import F, Dispatcher, Router
from aiogram.enums import ChatType
from aiogram.types import (
    Message,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    CallbackQuery,
)
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from bson import ObjectId
from datetime import datetime, timedelta, timezone
from pymongo.database import Database

from feedback_service import (
    admin_feedback_reply_handler,
    send_feedback,
    store_message_mapping,
    user_feedback_reply_handler,
)
from constants.dorms import DORM_KEYBOARD
from constants.order_types import OrderType, ORDER_TYPE_NAMES, ORDER_TYPE_CHAT_THREADS
from constants.order_statuses import OrderStatus, ORDER_STATUS_NAMES

from config import ADMIN_CHAT_ID, AFTER_HOURS_PHONE, TIMEZONE_OFFSET

from states.feedback import FeedbackStates
from states.request_form import RequestForm

from utils.delete_last_message import delete_last_message
from utils.get_queue_position import get_queue_position
from utils.get_status_keyboard import get_status_keyboard
from utils.is_valid_ukraine_phone import is_valid_ukraine_phone
from utils.is_within_work_hours import is_within_work_hours
from utils.str_to_digits_id import srt_to_digits_id

from google_sheets_service import add_order_to_sheet, update_order_status_in_sheet

router = Router()

private_router = Router()
private_router.message.filter(F.chat.type == ChatType.PRIVATE)


cancel_order_btn = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text="❌ Скасувати", callback_data="cancel_request")]
    ]
)

cancel_feedback_btn = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text="❌ Закрити", callback_data="cancel_feedback")]
    ]
)


def back_btn(target) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="⬅ Назад", callback_data=f"back:{target}")]
        ]
    )


def register_handlers(dp: Dispatcher, db: Database) -> None:
    dp.include_router(router)
    dp.include_router(private_router)

    @router.message(Command("start"))
    async def start(msg: Message) -> None:
        await msg.answer(
            "Привіт! Це бот служби експлуатації гуртожитків КПІ.\n\n"
            "У неробочий час (з 17:15 до 8:30 у будні і цілодобово у вихідні) послуги для усунення аварійної ситуації виконує чергова зміна.\n\n"
            "У робочий час ремонтні роботи виконують працівники дільниць служби експлуатації.\n\n"
            "Робочі години: будні з 9:00 до 17:00."
        )

    @private_router.message(Command("request"))
    async def req(msg: Message, state: FSMContext) -> None:
        await state.set_state(RequestForm.name)
        message = await msg.answer(
            "Введіть ПІБ (наприклад: Іваненко Іван Іванович)",
            reply_markup=cancel_order_btn,
        )
        await state.update_data(last_message_id=message.message_id)

    @private_router.callback_query(F.data == "cancel_request")
    async def cancel_order(call: CallbackQuery, state: FSMContext) -> None:
        await state.clear()
        await call.message.edit_text("Заявка скасована")

    @private_router.message(RequestForm.name)
    async def get_name(msg: Message, state: FSMContext) -> None:
        await delete_last_message(msg, state)
        await state.set_state(RequestForm.phone)
        message = await msg.answer(
            "Введіть номер телефону (наприклад: +380991234567)",
            reply_markup=back_btn("name"),
        )
        await state.update_data(name=msg.text, last_message_id=message.message_id)

    @private_router.message(RequestForm.phone)
    async def get_phone(msg: Message, state: FSMContext) -> None:
        await delete_last_message(msg, state)

        phone = msg.text
        if not phone or not is_valid_ukraine_phone(phone):
            message = await msg.answer(
                "Неправильний формат номеру телефону. Приклад: +380991234567. Повторіть ввід",
                reply_markup=back_btn("name"),
            )
            await state.update_data(last_message_id=message.message_id)
            return

        await state.set_state(RequestForm.dorm)
        message = await msg.answer(
            "Оберіть номер гуртожитку", reply_markup=DORM_KEYBOARD
        )
        await state.update_data(phone=phone, last_message_id=message.message_id)

    @private_router.callback_query(F.data.startswith("dorm:"))
    async def get_dorm(call: CallbackQuery, state: FSMContext) -> None:
        selected_dorm = call.data.split(":", 1)[1]
        await delete_last_message(call.message, state)
        await state.set_state(RequestForm.problem_type)

        buttons = [
            [
                InlineKeyboardButton(
                    text=ORDER_TYPE_NAMES[t], callback_data=f"ptype:{t.name}"
                )
            ]
            for t in OrderType
        ]
        buttons.append(
            [InlineKeyboardButton(text="⬅ Назад", callback_data="back:dorm")]
        )

        message = await call.message.answer(
            "Виберіть тип проблеми",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons),
        )
        await state.update_data(dorm=selected_dorm, last_message_id=message.message_id)

    @private_router.callback_query(F.data.startswith("ptype:"))
    async def problem_type_callback(call: CallbackQuery, state: FSMContext) -> None:
        selected_type = OrderType[call.data.split(":", 1)[1]]
        await delete_last_message(call.message, state)
        await state.set_state(RequestForm.details)

        message = await call.message.answer(
            "Опишіть проблему, вкажіть кімнату, поверх, блок/крило та зручний час для візиту.",
            reply_markup=back_btn("problem_type"),
        )
        await state.update_data(
            problem_type=selected_type.value, last_message_id=message.message_id
        )

    @private_router.message(RequestForm.details)
    async def get_details(msg: Message, state: FSMContext) -> None:
        await delete_last_message(msg, state)

        data = await state.get_data()

        order_type = OrderType[data["problem_type"]]
        thread_id = ORDER_TYPE_CHAT_THREADS[order_type]

        forwarded_msg = None
        if msg.content_type != "text":
            forwarded_msg = await msg.forward(
                ADMIN_CHAT_ID, message_thread_id=thread_id
            )

        timestamp = datetime.now(timezone.utc) + timedelta(hours=TIMEZONE_OFFSET)

        if is_within_work_hours(timestamp):
            info_msg = "Очікуйте на відповідь"
        else:
            info_msg = "Зараз неробочий час, тому вона буде розглянута вранці"

            if AFTER_HOURS_PHONE:
                info_msg += f". У разі аварійної ситуації телефонуйте за номером: {AFTER_HOURS_PHONE}"

        forwarded_message_id = forwarded_msg.message_id if forwarded_msg else None

        order_data = {
            "name": data["name"],
            "phone": data["phone"],
            "dorm": data["dorm"],
            "problem_type": data["problem_type"],
            "details": msg.text or msg.caption,
            "forwarded_message_id": forwarded_msg.message_id if forwarded_msg else None,
            "status": OrderStatus.WAITING.value,
            "timestamp": timestamp,
            "edit_timestamp": timestamp,
            "user_id": msg.from_user.id,
        }

        result = await db.requests.insert_one(order_data)
        request_id = str(result.inserted_id)
        request_digits_id = srt_to_digits_id(request_id)
        msg_text = (
            f"Нова заявка #{request_digits_id}\n"
            f"ПІБ: {order_data['name']}\n"
            f"Телефон: {order_data['phone']}\n"
            f"Гуртожиток: {order_data['dorm']}\n"
            f"Тип: {ORDER_TYPE_NAMES[order_type]}\n"
        )

        if forwarded_msg is None:
            msg_text += f"Опис: {order_data['details']}\n"

        msg_text += f"Статус: {ORDER_STATUS_NAMES[OrderStatus.WAITING]}"

        queue_position = await get_queue_position(db.requests, order_type, timestamp)
        user_message = await msg.answer(
            f"Заявка #{request_digits_id} відправлена.\n"
            f"{info_msg}. Якщо бажаєте додати більше інформації, відправте реплай на це повідомлення.\n"
            f"Позиція в черзі: {queue_position}"
        )
        admin_message = await msg.bot.send_message(
            ADMIN_CHAT_ID,
            msg_text,
            message_thread_id=thread_id,
            reply_markup=get_status_keyboard(OrderStatus.WAITING, request_id),
            parse_mode=None,
        )
        await state.clear()
        await store_message_mapping(
            db,
            msg.from_user.id,
            user_message.message_id,
            admin_message.message_id,
            forwarded_message_id,
            True if forwarded_msg else None,
        )

        admin_chat_id_str = re.sub(r"^-100", "", str(ADMIN_CHAT_ID))
        telegram_url = (
            f"https://t.me/c/{admin_chat_id_str}/{thread_id}/{admin_message.message_id}"
        )

        try:
            add_order_to_sheet(request_digits_id, telegram_url, order_data)
        except Exception as e:
            print(e)
            await msg.bot.send_message(
                ADMIN_CHAT_ID,
                "Не вдалось додати запис в таблицю",
                message_thread_id=thread_id,
            )

    @router.callback_query(F.data.startswith("status:"))
    async def update_status(call: CallbackQuery, state: FSMContext) -> None:
        _, status_str, request_id = call.data.split(":")
        status = OrderStatus[status_str]

        request = await db.requests.find_one({"_id": ObjectId(request_id)})
        if not request:
            await call.answer("Заявку не знайдено", show_alert=True)
            return

        edit_timestamp = datetime.now(timezone.utc) + timedelta(hours=TIMEZONE_OFFSET)

        await db.requests.update_one(
            {"_id": ObjectId(request_id)},
            {"$set": {"status": status.value, "edit_timestamp": edit_timestamp}},
        )

        request_digits_id = srt_to_digits_id(request_id)
        user_message = await call.bot.send_message(
            request["user_id"],
            f"Статус заявки #{request_digits_id} оновлено: {ORDER_STATUS_NAMES[status]}",
        )

        order_type = OrderType[request["problem_type"]]

        msg_text = (
            f"Заявка #{request_digits_id}\n"
            f"ПІБ: {request['name']}\n"
            f"Телефон: {request['phone']}\n"
            f"Гуртожиток: {request['dorm']}\n"
            f"Тип: {ORDER_TYPE_NAMES[order_type]}\n"
        )

        if request["details"]:
            msg_text += f"Опис: {request['details']}\n"

        msg_text += f"Статус: {ORDER_STATUS_NAMES[status]}"

        await call.message.edit_text(
            msg_text,
            reply_markup=get_status_keyboard(status, request_id),
        )

        await store_message_mapping(
            db, request["user_id"], user_message.message_id, call.message.message_id
        )

        try:
            update_order_status_in_sheet(
                request_digits_id, status, order_type, edit_timestamp
            )
        except Exception as e:
            print(e)
            await call.bot.send_message(
                ADMIN_CHAT_ID,
                "Не вдалось оновити статус в таблиці",
                message_thread_id=call.message.message_thread_id,
            )

    @private_router.callback_query(F.data.startswith("back:"))
    async def go_back(call: CallbackQuery, state: FSMContext) -> None:
        target = call.data.split(":")[1]

        if target == "problem_type":
            await state.set_state(RequestForm.problem_type)
            buttons = [
                [
                    InlineKeyboardButton(
                        text=ORDER_TYPE_NAMES[t], callback_data=f"ptype:{t.name}"
                    )
                ]
                for t in OrderType
            ]

            buttons.append(
                [InlineKeyboardButton(text="⬅ Назад", callback_data="back:dorm")]
            )

            message = await call.message.edit_text(
                "Виберіть тип проблеми",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons),
            )

            await state.update_data(last_message_id=message.message_id)
        elif target == "dorm":
            await state.set_state(RequestForm.dorm)
            message = await call.message.edit_text(
                "Оберіть номер гуртожитку",
                reply_markup=DORM_KEYBOARD,
            )
            await state.update_data(last_message_id=message.message_id)
        elif target == "phone":
            await state.set_state(RequestForm.phone)
            message = await call.message.edit_text(
                "Введіть номер телефону (наприклад: +380991234567)",
                reply_markup=back_btn("name"),
            )
            await state.update_data(last_message_id=message.message_id)
        elif target == "name":
            await state.set_state(RequestForm.name)
            message = await call.message.edit_text(
                "Введіть ПІБ (наприклад: Іваненко Іван Іванович)",
                reply_markup=cancel_order_btn,
            )
            await state.update_data(last_message_id=message.message_id)

        await call.answer()

    @router.message(Command("status"))
    async def status(msg: Message) -> None:
        user_id = msg.from_user.id
        requests = (
            await db.requests.find({"user_id": user_id})
            .sort("timestamp", -1)
            .to_list(length=None)
        )

        if not requests:
            await msg.answer("У вас немає заявок.")
            return

        response = f"Усього заявок: {len(requests)}\n\n"

        for request in requests:
            order_type = OrderType[request["problem_type"]]
            status = OrderStatus(request["status"])
            request_id = str(request["_id"])
            request_digits_id = srt_to_digits_id(request_id)

            response += f"#{request_digits_id}\n"
            response += f"Тип: {ORDER_TYPE_NAMES[order_type]}\n"
            response += f"Гуртожиток: {request['dorm']}\n"

            if request["details"]:
                response += f"Опис: {request['details']}\n"

            response += f"Статус: {ORDER_STATUS_NAMES[status]}\n"

            if status == OrderStatus.IN_PROGRESS or status == OrderStatus.WAITING:
                queue_position = await get_queue_position(
                    db.requests, order_type, request["timestamp"]
                )
                response += f"Позиція в черзі: {queue_position}\n"

            response += "\n"

        await msg.answer(response)

    @private_router.message(Command("tasks"))
    async def tasks(msg: Message) -> None:
        total_in_progress = 0
        in_progress_by_type = {}

        pipeline = [
            {"$match": {"status": OrderStatus.IN_PROGRESS.value}},
            {"$group": {"_id": "$problem_type", "count": {"$sum": 1}}},
        ]
        async for doc in db.requests.aggregate(pipeline):
            try:
                order_type = OrderType[doc["_id"]]
                count = doc["count"]
                in_progress_by_type[order_type] = count
                total_in_progress += count
            except KeyError:
                continue

        response = f"Заявки у роботі ({total_in_progress}):\n"

        for order_type in OrderType:
            count = in_progress_by_type.get(order_type, 0)
            response += f"{ORDER_TYPE_NAMES[order_type]} – {count}\n"

        await msg.answer(response.rstrip())

    @private_router.callback_query(F.data == "cancel_feedback")
    async def cancel_feedback(call: CallbackQuery, state: FSMContext) -> None:
        await state.clear()
        await call.message.delete()

    @private_router.message(Command("feedback"))
    async def feedback(msg: Message, state: FSMContext) -> None:
        await state.set_state(FeedbackStates.feedback)
        answer = await msg.answer(
            "📩 Надішли сюди будь-яке повідомлення, і ми його отримаємо.\n"
            '❌ Якщо передумав, натисни "Закрити".',
            reply_markup=cancel_feedback_btn,
        )
        await state.update_data(last_message_id=answer.message_id)

    @private_router.message(FeedbackStates.feedback)
    async def feedback_sent(msg: Message, state: FSMContext) -> None:
        await send_feedback(msg, db)
        await delete_last_message(msg, state)
        answer = await msg.answer(
            'Ваше повідомленя надіслано! За потреби надішліть ще одне, або натисність "Закрити".',
            reply_markup=cancel_feedback_btn,
        )
        await state.update_data(last_message_id=answer.message_id)

    @private_router.message(F.reply_to_message)
    async def user_feedback_handler(msg: Message) -> None:
        await user_feedback_reply_handler(msg, db)

    @router.message(F.reply_to_message, F.chat.id == ADMIN_CHAT_ID)
    async def admin_feedback_handler(msg: Message) -> None:
        await admin_feedback_reply_handler(msg, db)

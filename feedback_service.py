from typing import List, Optional
from aiogram import Bot
from aiogram.types import (
    Message,
    MessageEntity,
    User,
    ReactionTypeEmoji,
    UNSET_PARSE_MODE,
)
from aiogram.exceptions import TelegramBadRequest
from pymongo.database import Database

from config import ADMIN_CHAT_ID, CHAT_THREAD_FEEDBACK


async def store_message_mapping(
    db: Database,
    user_id: int,
    user_message_id: int,
    admin_message_id: int,
    info_message_id: Optional[int] = None,
    is_info_message_admin: Optional[bool] = None,
) -> None:
    if (info_message_id is not None) != (is_info_message_admin is not None):
        raise ValueError(
            "Both info_message_id and is_info_message_admin must be set together."
        )

    message_mapping = {
        "user_id": user_id,
        "user_message_id": user_message_id,
        "admin_message_id": admin_message_id,
    }

    if info_message_id is None:
        await db.feedback.insert_one(message_mapping)
        return

    if is_info_message_admin:
        info_user_message = user_message_id
        info_admin_message = info_message_id
    else:
        info_user_message = info_message_id
        info_admin_message = admin_message_id

    info_message_mapping = {
        "user_id": user_id,
        "user_message_id": info_user_message,
        "admin_message_id": info_admin_message,
    }

    await db.feedback.insert_many([message_mapping, info_message_mapping])


async def get_user_message_id(
    db: Database, admin_message_id: int
) -> tuple[int, int] | tuple[None, None]:
    doc = await db.feedback.find_one({"admin_message_id": admin_message_id})
    if doc:
        return doc["user_id"], doc["user_message_id"]

    return None, None


async def get_admin_message_id(
    db: Database, user_id: int, user_message_id: int
) -> Optional[int]:
    doc = await db.feedback.find_one(
        {"user_id": user_id, "user_message_id": user_message_id}
    )

    return doc["admin_message_id"] if doc else None


async def send_message_with_reply(
    chat_id: int,
    reply_message_id: int,
    message_text: str,
    bot: Bot,
    thread: Optional[int] = None,
    entities: Optional[List[MessageEntity]] = None,
    parse_mode: str | None = UNSET_PARSE_MODE,
) -> Message:
    try:
        return await bot.send_message(
            chat_id,
            message_text,
            message_thread_id=thread,
            protect_content=False,
            entities=entities,
            reply_to_message_id=reply_message_id,
            parse_mode=parse_mode,
        )
    except TelegramBadRequest as e:
        if e.message != "Bad Request: message to be replied not found":
            raise e

        return await bot.send_message(
            chat_id,
            message_text,
            message_thread_id=thread,
            protect_content=False,
            entities=entities,
            parse_mode=parse_mode,
        )


def adjust_entities_and_message_text(
    prefix: str,
    text: str,
    entities: Optional[List[MessageEntity]],
    user: Optional[User] = None,
) -> tuple[str, list[MessageEntity]]:
    full_name = user.full_name if user else ""
    full_name_length = len(full_name.encode("utf-16-le")) // 2

    new_entities = []

    if user:
        new_entities.append(
            MessageEntity(
                type="code",
                offset=len(prefix.encode("utf-16-le")) // 2,
                length=full_name_length,
            )
        )

        prefix += full_name

        username = user.username
        if username:
            new_entities.append(
                MessageEntity(
                    type="url",
                    offset=(len(prefix.encode("utf-16-le")) // 2) + 2,
                    length=len(username) + 1,
                    url=f"https://t.me/{username}",
                )
            )

            prefix += f" (@{username})"

    prefix += ":\n\n"
    entity_offset = len(prefix.encode("utf-16-le")) // 2

    if entities:
        for entity in entities:
            adjusted_entity = entity.model_copy()
            adjusted_entity.offset += entity_offset
            new_entities.append(adjusted_entity)

    return prefix + text, new_entities


async def send_feedback(message: Message, db: Database):
    if message.from_user is None:
        return

    user_id = message.from_user.id
    message_id = message.message_id

    if message.text:
        user = message.from_user
        prefix = "📩 Нове повідомлення від "
        info_text, entities = adjust_entities_and_message_text(
            prefix,
            message.text,
            message.entities,
            user,
        )

        forwarded_message = await message.bot.send_message(
            ADMIN_CHAT_ID,
            info_text,
            message_thread_id=CHAT_THREAD_FEEDBACK,
            protect_content=False,
            entities=entities,
            parse_mode=None,
        )
        await store_message_mapping(
            db, user_id, message_id, forwarded_message.message_id
        )
        return

    full_name = message.from_user.full_name
    username = message.from_user.username
    username_label = (
        f' (<a href="https://t.me/{username}">@{username}</a>)' if username else ""
    )

    info_message = await message.bot.send_message(
        ADMIN_CHAT_ID,
        f"📩 Нове повідомлення від <code>{full_name}</code>{username_label}:",
        message_thread_id=CHAT_THREAD_FEEDBACK,
        parse_mode="HTML",
    )

    forwarded_message = await message.forward(
        ADMIN_CHAT_ID,
        CHAT_THREAD_FEEDBACK,
        protect_content=False,
    )

    await store_message_mapping(
        db,
        user_id,
        message_id,
        forwarded_message.message_id,
        info_message.message_id,
        True,
    )


async def user_feedback_reply_handler(message: Message, db: Database):
    if message.from_user is None:
        return

    user_id = message.from_user.id
    reply_message_id = message.reply_to_message.message_id
    admin_message_id = await get_admin_message_id(db, user_id, reply_message_id)

    if not admin_message_id:
        return

    if message.text:
        user = message.from_user
        prefix = "📨 Відповідь від "
        info_text, entities = adjust_entities_and_message_text(
            prefix,
            message.text,
            message.entities,
            user,
        )
        forwarded_message = await send_message_with_reply(
            ADMIN_CHAT_ID,
            admin_message_id,
            info_text,
            message.bot,
            entities=entities,
        )
        await store_message_mapping(
            db,
            user_id,
            message.message_id,
            forwarded_message.message_id,
        )
        return

    full_name = message.from_user.full_name
    username = message.from_user.username
    username_label = (
        f' (<a href="https://t.me/{username}">@{username}</a>)' if username else ""
    )

    info_message = await send_message_with_reply(
        ADMIN_CHAT_ID,
        admin_message_id,
        f"📨 Відповідь від <code>{full_name}</code>{username_label}:",
        message.bot,
        parse_mode="HTML",
    )

    forwarded_actual = await message.forward(
        ADMIN_CHAT_ID,
        message_thread_id=info_message.message_thread_id,
        protect_content=False,
    )

    await store_message_mapping(
        db,
        user_id,
        message.message_id,
        forwarded_actual.message_id,
        info_message.message_id,
        True,
    )


async def admin_feedback_reply_handler(message: Message, db: Database):
    user_id, user_message_id = await get_user_message_id(
        db, message.reply_to_message.message_id
    )

    if not user_id or not user_message_id:
        return

    await message.bot.set_message_reaction(
        message.chat.id,
        message.message_id,
        [ReactionTypeEmoji(emoji="❤")],
    )

    if message.text:
        info_text, entities = adjust_entities_and_message_text(
            "📨 Відповідь адміністраторів",
            message.text,
            message.entities,
        )
        forwarded_message = await send_message_with_reply(
            user_id, user_message_id, info_text, message.bot, entities=entities
        )
        await store_message_mapping(
            db,
            user_id,
            forwarded_message.message_id,
            message.message_id,
        )
        return

    info_message = await send_message_with_reply(
        user_id, user_message_id, "📨 Відповідь адміністраторів:", message.bot
    )
    forwarded_message = await message.bot.copy_message(
        user_id,
        message.chat.id,
        message.message_id,
        protect_content=False,
    )

    await store_message_mapping(
        db,
        user_id,
        forwarded_message.message_id,
        message.message_id,
        info_message.message_id,
        False,
    )

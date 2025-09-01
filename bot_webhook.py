from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, HTTPException
from aiogram import Bot, Dispatcher
from aiogram.types import Update

from config import BOT_TOKEN, WEBHOOK_SECRET, WEBHOOK_URL
from database import db, setup_indexes
from handlers import register_handlers

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
register_handlers(dp, db)


async def set_webhook():
    await bot.set_webhook(
        url=WEBHOOK_URL,
        secret_token=WEBHOOK_SECRET,
        allowed_updates=["message", "callback_query"],
        drop_pending_updates=True,
    )


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_indexes(db)

    await set_webhook()

    yield

    await bot.session.close()


app = FastAPI(lifespan=lifespan)


@app.get("/")
def health_check():
    return {"ok": True}


@app.get("/set_webhook")
async def set_webhook_handler():
    await set_webhook()

    return {"ok": True}


@app.post("/")
async def telegram_webhook(request: Request):
    try:
        raw_update = await request.json()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    update = Update.model_validate(raw_update, context={"bot": bot})

    await dp.feed_update(bot, update)

    return {"ok": True}

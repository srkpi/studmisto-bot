
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, HTTPException
from aiogram import Bot, Dispatcher
from aiogram.types import Update

from config import ADMIN_CHAT_ID, BOT_TOKEN, WEBHOOK_SECRET, WEBHOOK_URL
from database import db, setup_indexes
from handlers import register_handlers

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
register_handlers(dp, db)


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_indexes(db)
    await bot.set_webhook(url=WEBHOOK_URL, secret_token=WEBHOOK_SECRET)
    await bot.send_message(ADMIN_CHAT_ID, "Я запустився 🚀🤖⚡️")
    yield

    await bot.session.close()


app = FastAPI(lifespan=lifespan)


@app.get("/")
def health_check():
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

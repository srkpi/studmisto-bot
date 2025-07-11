from json import loads
from os import getenv
from dotenv import load_dotenv

load_dotenv('.dev-private.env')

BOT_TOKEN = getenv("BOT_TOKEN")

WEBHOOK_URL = getenv("WEBHOOK_URL")
WEBHOOK_SECRET = getenv("WEBHOOK_SECRET")

MONGO_URI = getenv("MONGO_URI")
ADMIN_CHAT_ID = int(getenv("ADMIN_CHAT_ID"))
CHAT_THREAD_FEEDBACK = int(getenv("CHAT_THREAD_FEEDBACK") or "0")

SPREADSHEET_ID = getenv("SPREADSHEET_ID")
GOOGLE_SERVICE_ACCOUNT_JSON = loads(getenv("GOOGLE_SERVICE_ACCOUNT_JSON"))

import logging

import uvicorn

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    uvicorn.run("bot_webhook:app", host="0.0.0.0", port=8000, reload=False)

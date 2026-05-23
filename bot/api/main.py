import os
import logging
from fastapi import FastAPI, Request, HTTPException
from aiogram.types import Update
from bot_logic import dp, bot

# Ensure webhook is set on startup (Vercel may restart frequently)


# Ensure logging goes to stdout (Vercel captures it)
logging.basicConfig(level=logging.INFO)

app = FastAPI()

@app.on_event("startup")
async def startup_event():
    # Set webhook to the URL defined in environment variable
    webhook_url = os.getenv("WEBHOOK_URL")
    if webhook_url:
        try:
            await bot.set_webhook(webhook_url)
            logging.info(f"Webhook set to {webhook_url}")
        except Exception as e:
            logging.error(f"Failed to set webhook: {e}")
    else:
        logging.warning("WEBHOOK_URL not set; webhook not configured.")

@app.post("/api/telegram")
async def telegram_webhook(request: Request):
    try:
        json_data = await request.json()
        update = Update(**json_data)
        await dp.feed_update(bot, update)
        return {"ok": True}
    except Exception as e:
        logging.exception("Webhook processing failed")
        raise HTTPException(status_code=500, detail=str(e))

# If you want a health check endpoint
@app.get("/api/health")
async def health_check():
    return {"status": "ok"}

import os
import asyncio
from aiogram import Bot
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv("TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")

if not TOKEN:
    raise RuntimeError("TOKEN env var not set")
if not WEBHOOK_URL:
    raise RuntimeError("WEBHOOK_URL env var not set")

async def main():
    bot = Bot(token=TOKEN)
    await bot.set_webhook(url=WEBHOOK_URL)
    print(f"✅ Webhook set to {WEBHOOK_URL}")
    await bot.session.close()

if __name__ == "__main__":
    asyncio.run(main())

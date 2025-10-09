from telegram import Bot

BOT_TOKEN = "7"
CHAT_ID = "-"

import asyncio

bot = Bot(token=BOT_TOKEN)

async def send_and_refresh_image(image_path, text):
    with open(image_path, "rb") as photo:
        await bot.send_photo(chat_id=CHAT_ID, photo=photo, caption=text)

    # await bot.send_message(chat_id=CHAT_ID, text=text)
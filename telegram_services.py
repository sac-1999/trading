from telegram import Bot


BOT_TOKEN = "7030049288:AAG8B3upzkm80oDq2QJTd25-K2aG63cfsTM"
CHAT_ID = "-1002132869398"

import asyncio

bot = Bot(token=BOT_TOKEN)

async def send_and_refresh_image(image_path, text):
    with open(image_path, "rb") as photo:
        await bot.send_photo(chat_id=CHAT_ID, photo=photo, caption=text)

async def send_trade(text):
    await bot.send_message(chat_id=CHAT_ID, text=text)
import asyncio
from telethon import TelegramClient

api_id = 27644731
api_hash = '934fe7edfed764fed5963fcac8266e85'
phone = '+4915566214361'
session_name = "F:/Telegram Dashboard/telegram_dashboard/Telegram-Uploader/session/latest_session.session"


client = TelegramClient(session_name, api_id, api_hash)

async def main():
    await client.start(phone=phone)  # will ask for code
    print("Logged in!")

with client:
    client.loop.run_until_complete(main())
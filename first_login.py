import asyncio
from telethon import TelegramClient

api_id = 24244805
api_hash = '8cf2f233f46fbdd89440589018a79feb'
phone = '+919327710301'
session_name = "F:/Telegram Dashboard/telegram_dashboard/Telegram-Uploader/session/latest_session.session"


client = TelegramClient(session_name, api_id, api_hash)

async def main():
    await client.start(phone=phone)  # will ask for code
    print("Logged in!")

with client:
    client.loop.run_until_complete(main())
import asyncio
from telethon import TelegramClient

api_id = 24244805
api_hash = '8cf2f233f46fbdd89440589018a79feb'
phone = '+919327710301'
session_name = "F:/Telegram Dashboard/telegram_dashboard/Telegram-Uploader/session/latest_session.session"

async def telegram_login():
    async with TelegramClient(session_name, api_id, api_hash) as client:
        # Step 1: Send code
        await client.connect()
        if not await client.is_user_authorized():
            await client.send_code_request(phone)
            code = input("Enter the code from Telegram: ")
            await client.sign_in(phone, code)
            print("Logged in successfully!")
        else:
            print("Already logged in!")

asyncio.run(telegram_login())

import streamlit as st
from telethon import TelegramClient, errors
import asyncio
from model import config, filter_files,convert_to_jpg

api_id = 24244805
api_hash = '8cf2f233f46fbdd89440589018a79feb'
phone = '+919327710301'
session_name = 'F:/Telegram Dashboard/telegram_dashboard/Telegram-Uploader/session/latest_session.session'

# Create Telegram client
client = TelegramClient(session_name, api_id, api_hash)

async def start_client(phone):
    await client.connect()
    if not await client.is_user_authorized():
        try:
            await client.send_code_request(phone)
        except errors.PhoneNumberInvalidError:
            st.error("Invalid phone number!")
            return False
        
        # Show input box in Streamlit to enter code
        code = st.text_input("Enter the code you received:")
        
        if code:
            try:
                await client.sign_in(phone, code)
                st.success("Logged in successfully!")
                return True
            except errors.SessionPasswordNeededError:
                # If 2FA password is enabled, ask for it
                password = st.text_input("Two-step verification password:", type="password")
                if password:
                    await client.start(password=password)
                    st.success("Logged in with 2FA!")
                    return True
            except errors.PhoneCodeInvalidError:
                st.error("Invalid code, please try again.")
                return False
    else:
        st.info("Already logged in!")
        return True

async def main():
    phone = st.text_input("Enter your phone number (with country code):")
    if phone and st.button("Login"):
        success = await start_client(phone)
        if success:
            # Continue with your app logic here
            pass

if __name__ == "__main__":
    asyncio.run(main())

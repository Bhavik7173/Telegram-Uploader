import os
import shutil
import asyncio
from datetime import datetime, date
from telethon import TelegramClient
from telethon.errors import FloodWaitError
from telethon.tl.types import DocumentAttributeFilename, MessageMediaPhoto
from telethon.errors import SessionPasswordNeededError
from model import config, filter_files,convert_to_jpg
import streamlit as st
from dotenv import load_dotenv

# === SUPPORTED TYPES ===
MEDIA_GROUP_TYPES = ('.jpg', '.jpeg', '.png', '.mp4', '.mov', '.mkv', '.pdf', '.docx', '.heic', '.webp')
OTHER_TYPES = ('.zip', '.rar', '.7z', '.txt', '.xls', '.ppt', '.exe')
SUPPORTED_EXTENSIONS = MEDIA_GROUP_TYPES + OTHER_TYPES

# session_name = config["session_name"]
# session_folder = os.path.join(os.getcwd(), "session")

load_dotenv()
BASE_PATH = os.getenv("BASE_PATH")

# Ensure folder exists
os.makedirs(BASE_PATH, exist_ok=True)

session_path = os.path.join(BASE_PATH, "my_session.session")

async def handle_upload(df_upload, mode, filter_method="None", filter_params=None):
    logs = []
    filter_params = filter_params or {}
    client = TelegramClient(session_path, config["api_id"], config["api_hash"])
    try:
        await client.start(phone=config["phone"])
    except SessionPasswordNeededError:
        # If user has 2FA password enabled
        password = os.getenv("TELEGRAM_PASSWORD")  # load from environment variable
        if not password:
            import streamlit as st
            password = st.text_input("🔑 Enter your Telegram 2FA Password", type="password")
        await client.sign_in(password=password)
    logs.append("✅ Logged into Telegram")


    uploaded = set()
    if os.path.exists(config["cache_file"]):
        with open(config["cache_file"], "r") as f:
            uploaded = set(line.strip() for line in f.readlines())

    for index, row in df_upload.iterrows():
        channel = str(row["Channel Link"]).strip()
        folder_raw = str(row["Actress"]).strip()

        if not folder_raw or folder_raw.lower() == "nan":
            logs.append(f"❌ Invalid folder name at row {index + 2}")
            continue

        folder = folder_raw if os.path.isabs(folder_raw) else os.path.join(config["base_path"], folder_raw)
        if not os.path.exists(folder):
            logs.append(f"❌ Folder not found: {folder}")
            continue

        try:
            entity = await client.get_entity(channel)
        except Exception as e:
            logs.append(f"❌ Cannot access channel: {folder}  ----->   {channel} | {e}")
            continue

        all_files = os.listdir(folder)
        files = [
            f for f in all_files
            if os.path.splitext(f)[1].lower() in SUPPORTED_EXTENSIONS
            and os.path.join(folder_raw, f) not in uploaded
        ]

                # Apply filtering here based on filter_method and filter_params
        files = filter_files(files, folder, filter_method, filter_params)

        if not files:
            logs.append(f"📁 No new files found in: {folder} after filtering")
            continue

        # if not files:
        #     logs.append(f"📁 No new files found in: {folder}")
        #     continue

        st.write(f"📤 Uploading {len(files)} files from: {folder}")
        progress_text = st.empty()
        bar = st.progress(0)
        # media_paths = [os.path.join(folder, f) for f in files]
        media_paths = [convert_to_jpg(os.path.join(folder, f)) for f in files]
        
        if mode == "Media Group":
            batch_size = 10
            for i in range(0, len(media_paths), batch_size):
                batch = media_paths[i:i+batch_size]
                uploaded_this_batch = False
                while not uploaded_this_batch:
                    try:
                        await client.send_file(entity, batch, caption=f"📤 Batch Upload on {date.today().strftime('%d/%m/%Y')}")
                        for f in batch:
                            filename = os.path.basename(f)
                            with open(config["temp_cache_file"], 'a') as fc:
                                fc.write(os.path.join(folder_raw, filename) + '\n')
                            with open(config["temp_log_file"], 'a') as fl:
                                fl.write(f"{datetime.now().isoformat()},{filename},{channel},Media\n")
                            try:
                                os.remove(f)
                            except Exception as e:
                                logs.append(f"❌ Could not delete {f}: {e}")
                            if f.endswith(".jpg") and not filename in all_files:
                                try:
                                    os.remove(f)
                                except Exception as e:
                                    logs.append(f"❌ Could not delete {f}: {e}")
                        uploaded_this_batch = True
                        bar.progress(min((i + batch_size) / len(media_paths), 1.0))
                        progress_text.text(f"📤 Uploaded {min(i + batch_size, len(media_paths))}/{len(media_paths)} files")
                    except FloodWaitError as e:
                        logs.append(f"⏳ FloodWait: Sleeping for {e.seconds} seconds")
                        await asyncio.sleep(e.seconds)
                    except Exception as e:
                        logs.append(f"❌ Media group batch upload failed: {e}")
                        uploaded_this_batch = True

        else:  # One-by-One
            for i, file in enumerate(files):
                path = os.path.join(folder, file)
                uploaded_this_file = False
                while not uploaded_this_file:
                    try:
                        await client.send_file(entity, path, caption=file + "\n" + f"Batch Upload on {date.today().strftime('%d/%m/%Y')}")
                        with open(config["temp_cache_file"], 'a') as f:
                            f.write(os.path.join(folder_raw, file) + '\n')
                        with open(config["temp_log_file"], 'a') as f:
                            f.write(f"{datetime.now().isoformat()},{file},{channel},Uploaded\n")
                        try:
                            os.remove(path)
                        except Exception as e:
                            logs.append(f"❌ Could not delete {file}: {e}")
                        # Delete temp jpg if converted
                        if path.endswith(".jpg") and not file.endswith(".jpg"):
                            try:
                                os.remove(path)
                            except Exception as e:
                                logs.append(f"❌ Could not delete temp file {path}: {e}")
                        bar.progress((i + 1) / len(files))
                        progress_text.text(f"📤 Uploaded {i+1}/{len(files)} files")
                        uploaded_this_file = True
                    except FloodWaitError as e:
                        logs.append(f"⏳ FloodWait: Sleeping for {e.seconds} seconds")
                        await asyncio.sleep(e.seconds)
                    except Exception as e:
                        logs.append(f"❌ Upload failed: {file} | {e}")
                        uploaded_this_file = True

        logs.append(f"✅ Completed upload for: {folder}  ----->   {channel}")

    await client.disconnect()

    # Save logs and cache
    if os.path.exists(config["temp_log_file"]):
        with open(config["temp_log_file"], "r") as temp_log, open(config["log_file"], "a") as main_log:
            shutil.copyfileobj(temp_log, main_log)

    if os.path.exists(config["temp_cache_file"]):
        with open(config["temp_cache_file"], "r") as temp_cache, open(config["cache_file"], "a") as main_cache:
            shutil.copyfileobj(temp_cache, main_cache)

    return logs


async def send_mobile_files(channel_link, uploaded_files, st, config):
    logs = []
    client = TelegramClient(config["session_name"] + "_mobile", config["api_id"], config["api_hash"])
    try:
        await client.start(phone=config["phone"])
    except SessionPasswordNeededError:
        # If user has 2FA password enabled
        password = os.getenv("TELEGRAM_PASSWORD")  # load from environment variable
        if not password:
            import streamlit as st
            password = st.text_input("🔑 Enter your Telegram 2FA Password", type="password")
        await client.sign_in(password=password)
    try:
        entity = await client.get_entity(channel_link)
    except Exception as e:
        st.error(f"❌ Failed to access channel: {channel_link} | {e}")
        return

    for file in uploaded_files:
        try:
            await client.send_file(entity, file, caption=file.name)
            with open(config["log_file"], 'a') as f:
                f.write(f"{datetime.now().isoformat()},{file.name},{channel_link},mobile\n")
            logs.append(f"✅ Uploaded: {file.name}")
        except Exception as e:
            logs.append(f"❌ Failed: {file.name} | {e}")
    await client.disconnect()
    return logs


async def download_media_from_channel(channel_username, save_path, st, config):
    os.makedirs(save_path, exist_ok=True)
    downloaded = 0
    client = TelegramClient(config["session_name"] + '_dl', config["api_id"], config["api_hash"])
    try:
        await client.start(phone=config["phone"])
    except SessionPasswordNeededError:
        # If user has 2FA password enabled
        password = os.getenv("TELEGRAM_PASSWORD")  # load from environment variable
        if not password:
            import streamlit as st
            password = st.text_input("🔑 Enter your Telegram 2FA Password", type="password")
        await client.sign_in(password=password)
    entity = await client.get_entity(channel_username)
    async for message in client.iter_messages(entity):
        if message.media:
            try:
                filename = None
                if message.file and message.file.name:
                    filename = message.file.name
                elif isinstance(message.media, MessageMediaPhoto):
                    filename = f"photo_{message.id}.jpg"
                elif message.document:
                    for attr in message.document.attributes:
                        if isinstance(attr, DocumentAttributeFilename):
                            filename = attr.file_name
                if not filename:
                    ext = message.file.ext or ".bin"
                    filename = f"file_{message.id}{ext}"
                save_file = os.path.join(save_path, filename)
                if not os.path.exists(save_file):
                    await message.download_media(file=save_file)
                    downloaded += 1
            except Exception as e:
                st.warning(f"❌ Error downloading media: {e}")
    await client.disconnect()
    return downloaded

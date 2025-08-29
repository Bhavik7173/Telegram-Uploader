# model.py

import os
import shutil
from datetime import datetime, date
from telethon import TelegramClient
from telethon.errors import FloodWaitError
from telethon.tl.types import DocumentAttributeFilename, MessageMediaPhoto
import asyncio
import pandas as pd
from PIL import Image
# import pillow_heif
import tempfile

# === Config ===
config = {
    # "api_id": int(os.getenv("TELEGRAM_API_ID")),
    # "api_hash": os.getenv("TELEGRAM_API_HASH"),
    # "phone": os.getenv("TELEGRAM_PHONE"),
    "api_id": 27644731,
    "api_hash": '934fe7edfed764fed5963fcac8266e85',
    "phone": '+4915566214361',
    "session_name": "latest_session.session",
    "base_path": "D:\TeraBoxDownload\Telegram\Telegram Upload\Files\Story",
    "log_file": "F:/Telegram Dashboard/telegram_dashboard/Telegram-Uploader/Log File/upload_log.csv",
    "temp_log_file": "F:/Telegram Dashboard/telegram_dashboard/Telegram-Uploader/Log File/temp_upload_log.csv",
    "cache_file": "F:/Telegram Dashboard/telegram_dashboard/Telegram-Uploader/Log File/uploaded_cache.txt",
    "temp_cache_file": "F:/Telegram Dashboard/telegram_dashboard/Telegram-Uploader/Log File/temp_uploaded_cache.txt"
}

def load_metrics(base_path, cache_file):
    folders = len(os.listdir(base_path)) if os.path.exists(base_path) else 0
    files = sum(len(f) for _, _, f in os.walk(base_path)) if os.path.exists(base_path) else 0
    uploads = len(open(cache_file).readlines()) if os.path.exists(cache_file) else 0
    return folders, files, uploads

def load_logs(log_file):
    if os.path.exists(log_file):
        try:
            df_log = pd.read_csv(log_file, names=["Timestamp", "File", "Channel", "FileType"])
            channels = df_log["Channel"].nunique()
            return df_log, channels
        except:
            return pd.DataFrame(), 0
    else:
        return pd.DataFrame(), 0
    
def filter_files(files, folder, filter_method, filter_params):
    if filter_method == "None":
        return files

    filtered = []

    if filter_method == "Name":
        name_filter = filter_params.get('name_filter', '').lower()
        if not name_filter:
            return files  # No filter text, return all
        # return filter_files_by_name_range(files, name_filter)
        filtered = [f for f in files if name_filter in f.lower()]

    elif filter_method == "Date":
        start_date = filter_params.get('start_date')
        end_date = filter_params.get('end_date')
        if not start_date or not end_date:
            return files  # Dates not properly set
        for f in files:
            file_path = os.path.join(folder, f)
            mod_time = os.path.getmtime(file_path)
            mod_date = datetime.fromtimestamp(mod_time).date()
            if start_date <= mod_date <= end_date:
                filtered.append(f)

    elif filter_method == "Size":
        min_size = filter_params.get('min_size', 0)
        max_size = filter_params.get('max_size', 0)
        for f in files:
            file_path = os.path.join(folder, f)
            size_kb = os.path.getsize(file_path) / 1024
            if size_kb >= min_size and (max_size == 0 or size_kb <= max_size):
                filtered.append(f)

    else:
        return files

    return filtered

def convert_to_jpg(path):
    try:
        ext = os.path.splitext(path)[1].lower()
        if ext == ".webp" or ext == ".heic":
            heif_file = None
            with Image.open(path) as im:
                rgb_im = im.convert("RGB")
                fd, new_path = tempfile.mkstemp(suffix=".jpg")
                os.close(fd)  # Close the file descriptor
                rgb_im.save(new_path, format="JPEG")
                return new_path
    except Exception as e:
        print(f"Error converting {path} to JPG: {e}")
    return path

def filter_files_by_name_range(files, name_filter):
    """
    Filters files whose names start with any letter in the range specified.
    Example input: "A-H" filters files starting with letters A, B, C, ..., H.
    """
    name_filter = name_filter.strip()
    filtered = []

    # Detect if input is in form X-Y (e.g. A-H)
    if len(name_filter) == 3 and name_filter[1] == '-':
        start_letter = name_filter[0].upper()
        end_letter = name_filter[2].upper()
        if start_letter.isalpha() and end_letter.isalpha() and start_letter <= end_letter:
            valid_letters = [chr(c) for c in range(ord(start_letter), ord(end_letter) + 1)]
            for f in files:
                first_char = f[0].upper() if f else ''
                if first_char in valid_letters:
                    filtered.append(f)
            return filtered

    # Otherwise treat as substring filter (case-insensitive)
    return [f for f in files if name_filter.lower() in f.lower()]

# # === SUPPORTED TYPES ===
# MEDIA_GROUP_TYPES = ('.jpg', '.jpeg', '.png', '.mp4', '.mov', '.mkv', '.pdf', '.docx', '.heic', '.webp')
# OTHER_TYPES = ('.zip', '.rar', '.7z', '.txt', '.xls', '.ppt', '.exe')
# SUPPORTED_EXTENSIONS = MEDIA_GROUP_TYPES + OTHER_TYPES


# # === UPLOAD FILES ===
# async def upload_files(upload_df, mode,
#                        base_path, session_name,
#                        api_id, api_hash, phone,
#                        log_file, temp_log_file,
#                        cache_file, temp_cache_file,
#                        st):
#     logs = []
#     uploaded = set()

#     if os.path.exists(cache_file):
#         with open(cache_file, 'r') as f:
#             uploaded = set(line.strip() for line in f)

#     client = TelegramClient(session_name, api_id, api_hash)
#     await client.start(phone=phone)
#     st.success("✅ Logged into Telegram")

#     for index, row in upload_df.iterrows():
#         channel = str(row.get('Channel Link', '')).strip()
#         folder_raw = str(row.get('Actress', '')).strip()

#         if not channel or not folder_raw or folder_raw.lower() == "nan":
#             logs.append(f"❌ Invalid data in row {index + 2}")
#             continue

#         folder = folder_raw if os.path.isabs(folder_raw) else os.path.join(base_path, folder_raw)
#         if not os.path.exists(folder):
#             logs.append(f"❌ Folder not found: {folder}")
#             continue

#         try:
#             entity = await client.get_entity(channel)
#         except Exception as e:
#             logs.append(f"❌ Cannot access channel {channel}: {e}")
#             continue

#         all_files = os.listdir(folder)
#         files = [
#             f for f in all_files
#             if os.path.splitext(f)[1].lower() in SUPPORTED_EXTENSIONS
#             and os.path.join(folder_raw, f) not in uploaded
#         ]

#         if not files:
#             logs.append(f"📁 No new files in: {folder}")
#             continue

#         st.write(f"📤 Uploading {len(files)} files from: {folder}")
#         progress_text = st.empty()
#         bar = st.progress(0)
#         media_paths = [os.path.join(folder, f) for f in files]

#         # Media Group Upload
#         if mode == "Media Group":
#             for i in range(0, len(media_paths), 10):
#                 batch = media_paths[i:i + 10]
#                 while True:
#                     try:
#                         await client.send_file(entity, batch, caption=f"📤 Batch Upload on {date.today().strftime('%d/%m/%Y')}")
#                         for f in batch:
#                             fname = os.path.basename(f)
#                             key = os.path.join(folder_raw, fname)
#                             with open(temp_cache_file, 'a') as fc:
#                                 fc.write(key + '\n')
#                             with open(temp_log_file, 'a') as fl:
#                                 fl.write(f"{datetime.now()},{key},{channel},Media\n")
#                             try:
#                                 os.remove(f)
#                             except Exception as e:
#                                 logs.append(f"❌ Could not delete {fname}: {e}")
#                         progress_text.text(f"📤 Uploaded {min(i + 10, len(media_paths))}/{len(media_paths)}")
#                         bar.progress(min((i + 10) / len(media_paths), 1.0))
#                         break
#                     except FloodWaitError as e:
#                         logs.append(f"⏳ FloodWait: Sleeping for {e.seconds} seconds")
#                         await asyncio.sleep(e.seconds)
#                     except Exception as e:
#                         logs.append(f"❌ Media group upload failed: {e}")
#                         break
#         else:
#             for i, file in enumerate(files):
#                 path = os.path.join(folder, file)
#                 key = os.path.join(folder_raw, file)
#                 while True:
#                     try:
#                         await client.send_file(entity, path, caption=file + "\n" + f"Batch Upload on {date.today().strftime('%d/%m/%Y')}")
#                         with open(temp_cache_file, 'a') as fc:
#                             fc.write(key + '\n')
#                         with open(temp_log_file, 'a') as fl:
#                             fl.write(f"{datetime.now()},{key},{channel},Uploaded\n")
#                         try:
#                             os.remove(path)
#                         except Exception as e:
#                             logs.append(f"❌ Could not delete {file}: {e}")
#                         progress_text.text(f"📤 Uploaded {i + 1}/{len(files)} files")
#                         bar.progress((i + 1) / len(files))
#                         break
#                     except FloodWaitError as e:
#                         logs.append(f"⏳ FloodWait: Sleeping for {e.seconds} seconds")
#                         await asyncio.sleep(e.seconds)
#                     except Exception as e:
#                         logs.append(f"❌ Upload failed: {file} | {e}")
#                         break
#         logs.append(f"✅ Completed upload for: {folder} → {channel}")

#     await client.disconnect()

#     if os.path.exists(temp_log_file):
#         with open(temp_log_file, 'r') as t, open(log_file, 'a') as m:
#             shutil.copyfileobj(t, m)
#     if os.path.exists(temp_cache_file):
#         with open(temp_cache_file, 'r') as t, open(cache_file, 'a') as m:
#             shutil.copyfileobj(t, m)

#     return logs


# # === MOBILE UPLOAD ===
# async def send_mobile_files(channel_link, uploaded_files, session_name, api_id, api_hash, phone, log_file, st):
#     logs = []
#     client = TelegramClient(session_name + "_mobile", api_id, api_hash)
#     await client.start(phone=phone)

#     try:
#         entity = await client.get_entity(channel_link)
#     except Exception as e:
#         st.error(f"❌ Failed to access channel: {channel_link} | {e}")
#         return

#     for file in uploaded_files:
#         try:
#             await client.send_file(entity, file, caption=os.path.basename(file.name))
#             with open(log_file, 'a') as f:
#                 f.write(f"{datetime.now().isoformat()},{file.name},{channel_link},mobile\n")
#             logs.append(f"✅ Uploaded: {file.name}")
#         except Exception as e:
#             logs.append(f"❌ Failed: {file.name} | {e}")

#     await client.disconnect()
#     return logs


# # === DOWNLOAD FROM CHANNEL ===
# async def download_media_from_channel(channel_username, save_path, session_name, api_id, api_hash, phone, st):
#     os.makedirs(save_path, exist_ok=True)
#     downloaded = 0
#     client = TelegramClient(session_name + '_dl', api_id, api_hash)
#     await client.start(phone=phone)

#     entity = await client.get_entity(channel_username)
#     async for message in client.iter_messages(entity):
#         if message.media:
#             try:
#                 filename = None
#                 if message.file and message.file.name:
#                     filename = message.file.name
#                 elif isinstance(message.media, MessageMediaPhoto):
#                     filename = f"photo_{message.id}.jpg"
#                 elif message.document:
#                     for attr in message.document.attributes:
#                         if isinstance(attr, DocumentAttributeFilename):
#                             filename = attr.file_name
#                 if not filename:
#                     ext = message.file.ext or ".bin"
#                     filename = f"file_{message.id}{ext}"
#                 save_file = os.path.join(save_path, filename)
#                 if not os.path.exists(save_file):
#                     await message.download_media(file=save_file)
#                     downloaded += 1
#             except Exception as e:
#                 st.warning(f"❌ Error downloading media: {e}")
#     await client.disconnect()
#     return downloaded

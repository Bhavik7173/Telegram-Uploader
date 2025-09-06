Streamlit Telegram Uploader Dashboard

A powerful Streamlit-based dashboard for managing Telegram uploads, downloads, analytics, and file automation. Built with Python + Telethon + Streamlit, this tool is designed to simplify working with Telegram channels, media, and Google Drive.


Features

📤 Uploads

Upload files to Telegram channels (single / batch / media groups).

Supports Excel-based automation (folders mapped to channels).

Avoids duplicate uploads with caching.

Progress tracking with tqdm.

📱 Mobile Upload

Upload files from mobile using Streamlit’s file_uploader.

Upload one-by-one or as media groups.

📡 My Channels

View channels you created.

Display channels in card layout.

Click for popup details & file downloads.

📥 Download Media

Download files from Telegram channels.

File separation based on Excel mapping.

☁ Google Drive

Upload/download files from Google Drive.

Cloud backup of uploaded media.

📊 Analytics

Pie charts (folder, file, channel counts).

Line charts (daily uploads).

Bar charts & filters (by channel, date).

Export logs & statistics.

🎨 Modern UI

Dark mode theme.

Tabs for navigation (Uploads, Mobile, Channels, Analytics, etc.).

Progress bars & success/error alerts.


🛠 Installation
1. Clone Repository
git clone https://github.com/your-username/telegram-uploader-dashboard.git
cd telegram-uploader-dashboard

2. Create Virtual Environment (Optional but Recommended)
python -m venv venv
source venv/bin/activate   # On Linux/Mac
venv\Scripts\activate      # On Windows

3. Install Requirements
pip install -r requirements.txt

4. Setup Telegram API

Go to my.telegram.org
.

Create a new app and get API_ID and API_HASH.

Add them in your .env file:

API_ID=your_api_id
API_HASH=your_api_hash
PHONE_NUMBER=+1234567890

5. Run Streamlit App
streamlit run app.py

# app.py
import streamlit as st
import pandas as pd
import plotly.express as px
import os, asyncio, shutil, time, hashlib
from controller import send_mobile_files,handle_upload, download_media_from_channel
from datetime import datetime, date, timedelta
from model import config, load_metrics, load_logs
import re
from dotenv import load_dotenv

load_dotenv()
BASE_PATH = os.getenv("BASE_PATH")
os.makedirs(BASE_PATH, exist_ok=True)
def clean_folder_name(name):
    # Remove characters not allowed in Windows file/folder names
    return re.sub(r'[<>:"/\\|?*\n\r\t]', '', name).strip()


# === PAGE SETUP ===
st.set_page_config(page_title="Telegram Dashboard", layout="wide")

# === SIDEBAR ===
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/2111/2111646.png", width=64)
    st.title("Telegram Dashboard")
    nav = st.radio("Menu", ["Dashboard", "Create Folders", "Separate Files", "Uploads", "Mobile Upload", "Download Media", "Folder Inspector", "Excel Sheet Manager", "Analytics", "Logs"])
    st.markdown("---")
    st.button("Settings")
    st.button("Help")
    st.button("Logout")

# === LOAD LOG DATA ===
if os.path.exists(config["log_file"]):
    try:
        df_log = pd.read_csv(config["log_file"], names=["Timestamp", "File", "Channel", "FileType"])
    except:
        df_log = pd.DataFrame(columns=["Timestamp", "File", "Channel", "FileType"])
else:
    df_log = pd.DataFrame(columns=["Timestamp", "File", "Channel", "FileType"])

# === NAVIGATION ===

if nav == "Dashboard":
    st.markdown("# 📊 Dashboard")

    folders = len(os.listdir(config["base_path"])) if os.path.exists(config["base_path"]) else 0
    files = sum(len(f) for _, _, f in os.walk(config["base_path"])) if os.path.exists(config["base_path"]) else 0
    uploads = len(open(config["cache_file"]).readlines()) if os.path.exists(config["cache_file"]) else 0
    channels = df_log["Channel"].nunique() if not df_log.empty else 0

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("📁 Total Folders", folders)
    col2.metric("📂 Total Files", files)
    col3.metric("✅ Uploaded", uploads)
    col4.metric("🔗 Channels", channels)

    st.markdown("---")
    chart1, chart2 = st.columns(2)
    if not df_log.empty:
        df_log["Timestamp"] = pd.to_datetime(df_log["Timestamp"], errors="coerce")
        df_chart = df_log[df_log["Timestamp"].notnull()]
        chart_data = df_chart.groupby(df_chart["Timestamp"].dt.date).size().reset_index(name="Uploads")
        chart1.subheader("📈 Uploads Over Time")
        chart1.plotly_chart(px.line(chart_data, x="Timestamp", y="Uploads", markers=True), use_container_width=True)

        chart2.subheader("📎 File Types")
        filetype_counts = df_chart["FileType"].value_counts().reset_index()
        filetype_counts.columns = ["FileType", "Count"]
        chart2.plotly_chart(px.pie(filetype_counts, names="FileType", values="Count"), use_container_width=True)
    else:
        chart1.info("No upload history yet.")
        chart2.info("No file type data available.")

    st.markdown("---")
    st.subheader("🏆 Top Channels by Uploads")
    if not df_log.empty:
        top_df = df_log["Channel"].value_counts().reset_index()
        top_df.columns = ["Channel", "Uploads"]
        st.dataframe(top_df.head(5), use_container_width=True)
    else:
        st.info("No upload log yet.")

elif nav == "Create Folders":
    st.subheader("Create Folders from Excel")
    with st.form("create_form"):
        excel_file = st.file_uploader("Upload Excel File", type=["xlsx"])
        create_base = st.text_input("Base Path", value=config["base_path"])
        column_name = st.text_input("Column Name for Folder Names")
        submitted = st.form_submit_button("Create Folders")
        if submitted and excel_file and create_base and column_name:
            df = pd.read_excel(excel_file)
            if column_name in df.columns:
                for name in df[column_name]:
                    if pd.notna(name):
                        folder_path = os.path.join(create_base, str(name).strip())
                        os.makedirs(folder_path, exist_ok=True)
                        st.success(f"Created folder: {folder_path}")
            else:
                st.error("❌ Column name not found in Excel")

elif nav == "Separate Files":
    st.subheader("Separate Files into Folders")
    with st.form("separate_form"):
        excel_file = st.file_uploader("Upload Excel File", type=["xlsx"])
        source_path = st.text_input("Source Folder Path")
        dest_path = st.text_input("Destination Base Folder")
        submitted = st.form_submit_button("Separate Files")
        if submitted and excel_file and source_path and dest_path:
            df = pd.read_excel(excel_file, header=None)
            username_to_folder = {}
            for _, row in df.iterrows():
                row = row.dropna().astype(str).tolist()
                if len(row) < 3:
                    continue
                folder_name = clean_folder_name(row[2])
                for cell in row[1:]:
                    cell = cell.strip().lower()
                    if cell.startswith("http") or cell.isdigit():
                        continue
                    if len(cell) >= 3:
                        username_to_folder[cell] = folder_name

            for folder in set(username_to_folder.values()):
                os.makedirs(os.path.join(dest_path, folder), exist_ok=True)
            os.makedirs(os.path.join(dest_path, "Other"), exist_ok=True)

            for filename in os.listdir(source_path):
                file_path = os.path.join(source_path, filename)
                if not os.path.isfile(file_path):
                    continue
                matched = False
                for username, folder_name in username_to_folder.items():
                    if filename.lower().startswith(username):
                        shutil.copy2(file_path, os.path.join(dest_path, folder_name, filename))
                        matched = True
                        break
                if not matched:
                    shutil.copy2(file_path, os.path.join(dest_path, "Other", filename))
            st.success("✅ Files separated and copied.")

# === UPLOADS TAB ===
elif nav == "Uploads":
    st.title("📤 Upload Manager")

    mode_select = st.radio("Choose upload mode", ["Excel Upload", "Manual Upload"])
    upload_type = st.radio("Upload Type", ["Media Group", "One-by-One"])

    # --- Add filter selection UI ---
    filter_method = st.selectbox("Filter files by:", ["None", "Name", "Date", "Size"])

    filter_params = {}

    if filter_method == "Name":
        name_filter = st.text_input("Enter part of filename to filter by:")
        filter_params['name_filter'] = name_filter.strip()

    elif filter_method == "Date":
        start_date = st.date_input("Start Date")
        end_date = st.date_input("End Date")
        filter_params['start_date'] = start_date
        filter_params['end_date'] = end_date

    elif filter_method == "Size":
        min_size = st.number_input("Min size (KB)", min_value=0)
        max_size = st.number_input("Max size (KB, 0 means no max)", min_value=0)
        filter_params['min_size'] = min_size
        filter_params['max_size'] = max_size
        
    if mode_select == "Excel Upload":
        excel_file = st.file_uploader("Upload Excel File (Channel Link + Actress)", type=["xlsx"])
        upload_btn = st.button("Start Upload")
        if excel_file and upload_btn:
            df_upload = pd.read_excel(excel_file)

            # Then on button click pass filter_params to handle_upload
            if excel_file and upload_btn:
                df_upload = pd.read_excel(excel_file)
                if "Channel Link" in df_upload.columns and "Actress" in df_upload.columns:
                    logs = asyncio.run(handle_upload(df_upload, mode=upload_type, filter_method=filter_method, filter_params=filter_params))
                    # for log in logs:
                    #     st.write(log)
                    for log in logs:
                        if log.startswith("✅"):
                            st.success(log)
                        elif log.startswith("❌"):
                            st.error(log)
                        elif log.startswith("⏳"):
                            st.warning(log)
                        else:
                            st.write(log)
                else:
                    st.error("Missing required columns in Excel: 'Channel Link' and 'Actress'")
                    
            # if "Channel Link" in df_upload.columns and "Actress" in df_upload.columns:
            #     logs = asyncio.run(handle_upload(df_upload, mode=upload_type))
            #     for log in logs:
            #         st.write(log)
            # else:
            #     st.error("Missing required columns in Excel: 'Channel Link' and 'Actress'")
    else:
        channel = st.text_input("Telegram Channel Link or Username")
        actress = st.text_input("Folder Name (Actress)")
        upload_btn2 = st.button("Upload Manually")
        if channel and actress and upload_btn2:
            df_upload = pd.DataFrame([{"Channel Link": channel, "Actress": actress}])
            logs = asyncio.run(handle_upload(df_upload, mode=upload_type))
            for log in logs:
                st.write(log)

elif nav == "Mobile Upload":
    
    st.title("📱 Upload Files from Mobile")
    channel = st.text_input("Telegram Channel Username or Link")
    files = st.file_uploader("Select files to upload", accept_multiple_files=True)
    if st.button("🚀 Upload Now") and channel and files:
        logs = asyncio.run(send_mobile_files(channel, files))
        for log in logs:
            st.success(log)

# === Download Media ===
elif nav == "Download Media":
    st.header("📥 Download Files from Telegram Channel")
    channel_link = st.text_input("Enter Telegram Channel Username or Link")
    save_path = st.text_input("Enter Download Folder Path", value="D:/TelegramDownloads")
    if st.button("Download All Media"):
        count = asyncio.run(download_media_from_channel(channel_link, save_path))
        st.success(f"✅ Downloaded {count} media files.")

elif nav == "Folder Inspector":
    st.header("🗂️ Folder Inspector & Cleaner")

    folder_path = st.text_input("Enter Folder Path to Inspect")

    def get_folder_stats(folder_path):
        total_size = 0
        total_files = 0
        for root, dirs, files in os.walk(folder_path):
            total_files += len(files)
            for f in files:
                fp = os.path.join(root, f)
                total_size += os.path.getsize(fp)
        return total_files, total_size

    def find_duplicates(folder_path):
        hashes = {}
        duplicates = []
        for root, dirs, files in os.walk(folder_path):
            for f in files:
                fp = os.path.join(root, f)
                with open(fp, 'rb') as file:
                    filehash = hashlib.md5(file.read()).hexdigest()
                if filehash in hashes:
                    duplicates.append((fp, hashes[filehash]))
                else:
                    hashes[filehash] = fp
        return duplicates

    def delete_old_files(folder_path, days_old=30):
        now = datetime.now()
        cutoff = now - timedelta(days=days_old)
        deleted_files = []
        for root, dirs, files in os.walk(folder_path):
            for f in files:
                fp = os.path.join(root, f)
                mtime = datetime.fromtimestamp(os.path.getmtime(fp))
                if mtime < cutoff:
                    os.remove(fp)
                    deleted_files.append(fp)
        return deleted_files

    def zip_folder(folder_path, output_path):
        shutil.make_archive(output_path, 'zip', folder_path)

    if folder_path and os.path.exists(folder_path):
        total_files, total_size = get_folder_stats(folder_path)
        st.write(f"Total files: {total_files}")
        st.write(f"Total size: {total_size / (1024*1024):.2f} MB")

        if st.button("Find Duplicate Files"):
            dups = find_duplicates(folder_path)
            if dups:
                st.warning(f"Found {len(dups)} duplicate files:")
                for dup in dups:
                    st.write(f"Duplicate: {dup[0]}  <--->  {dup[1]}")
            else:
                st.success("No duplicates found.")

        days_old = st.number_input("Delete files older than days", min_value=1, max_value=365, value=30)
        if st.button("Delete Old Files"):
            deleted = delete_old_files(folder_path, days_old)
            st.success(f"Deleted {len(deleted)} files older than {days_old} days.")

        if st.button("Zip Folder"):
            zip_output = folder_path.rstrip(os.sep) + "_zipped"
            zip_folder(folder_path, zip_output)
            st.success(f"Folder zipped to {zip_output}.zip")
    else:
        st.info("Enter a valid existing folder path.")


elif nav == "📄 Excel Sheet Manager":
    st.header("📄 Excel Sheet Viewer & Manager")

    uploaded_file = st.file_uploader("Upload Excel File", type=["xlsx"])
    if uploaded_file:
        df_excel = pd.read_excel(uploaded_file)
        st.dataframe(df_excel, use_container_width=True)

        if "Instagram Name" in df_excel.columns and "Actress" in df_excel.columns and "Channel Link" in df_excel.columns:
            st.success("✅ Sheet has required columns.")
        else:
            st.warning("⚠️ Required columns not found. Expected: 'Instagram', 'Folder', 'Channel Link'.")

        st.download_button(
            label="📥 Download Excel",
            data=df_excel.to_csv(index=False),
            file_name="insta_channel_map.csv",
            mime="text/csv"
        )
    else:
        st.info("📎 Upload your Excel file to view it here.")

# Analytics (placeholder)
elif nav == "Analytics":
    st.header("📈 Analytics")
    if not os.path.exists(config["log_file"]):
        st.warning("No logs found yet.")
    else:
        df = pd.read_csv(config["log_file"], names=["Timestamp", "File", "Channel", "FileType"])
        df["Timestamp"] = pd.to_datetime(df["Timestamp"], errors='coerce')
        df.dropna(subset=["Timestamp"], inplace=True)
        df["Date"] = df["Timestamp"].dt.date
        start = st.date_input("Start Date", df["Date"].min())
        end = st.date_input("End Date", df["Date"].max())
        channel_filter = st.multiselect("Channel Filter", df["Channel"].unique())
        type_filter = st.multiselect("File Type Filter", df["FileType"].unique())
        filtered = df[(df["Date"] >= start) & (df["Date"] <= end)]
        if channel_filter:
            filtered = filtered[filtered["Channel"].isin(channel_filter)]
        if type_filter:
            filtered = filtered[filtered["FileType"].isin(type_filter)]
        col1, col2 = st.columns(2)
        daily = filtered.groupby("Date").size().reset_index(name="Uploads")
        col1.plotly_chart(px.line(daily, x="Date", y="Uploads", title="Daily Upload Volume"), use_container_width=True)
        ftypes = filtered["FileType"].value_counts().reset_index()
        ftypes.columns = ["FileType", "Count"]
        col2.plotly_chart(px.pie(ftypes, names="FileType", values="Count", title="File Types"), use_container_width=True)
        ch_count = filtered["Channel"].value_counts().reset_index()
        ch_count.columns = ["Channel", "Uploads"]
        st.subheader("Uploads per Channel")
        st.plotly_chart(px.bar(ch_count, x="Channel", y="Uploads"), use_container_width=True)
        st.download_button("📥 Download Filtered Logs", filtered.to_csv(index=False), file_name="filtered_uploads.csv")

# === LOGS TAB ===
elif nav == "Logs":
    st.title("🧾 Upload Logs")
    if not df_log.empty:
        st.dataframe(df_log, use_container_width=True)
    else:
        st.info("No log file found yet.")
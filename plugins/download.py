from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
import os
import time
import asyncio
import hashlib
from database.database import db

# Dictionary to store file mappings
file_mappings = {}

# Handle video/document upload
@Client.on_message(filters.document | filters.video)
async def handle_video_upload(client: Client, message: Message):
    user_id = message.from_user.id
    
    # Check if user exists in database
    user = await db.get_user(user_id)
    if not user:
        await message.reply_text("❌ Please start the bot first using /start")
        return
    
    # Check file type
    if message.document:
        file = message.document
        file_name = file.file_name
        if not file_name or not any(file_name.lower().endswith(ext) for ext in ['.mp4', '.mkv', '.avi', '.mov', '.wmv', '.flv']):
            await message.reply_text("❌ Please send a valid video file!")
            return
    elif message.video:
        file = message.video
        file_name = f"video_{int(time.time())}.mp4"
    else:
        return
    
    # Check file size (limit 2GB)
    if file.file_size > 2 * 1024 * 1024 * 1024:
        await message.reply_text("❌ File size too large! Maximum 2GB allowed.")
        return
    
    # Create downloads directory if not exists
    if not os.path.exists("downloads"):
        os.makedirs("downloads")
    
    # Progress tracking variables
    last_update_time = 0
    
    # Download progress callback with 20-second limit
    async def progress(current, total):
        nonlocal last_update_time
        current_time = time.time()
        
        # Only update every 20 seconds
        if current_time - last_update_time >= 20:
            percent = (current / total) * 100
            try:
                await status_msg.edit_text(
                    f"📥 **Downloading...**\n"
                    f"📁 File: `{file_name}`\n"
                    f"📊 Progress: {percent:.1f}%\n"
                    f"💾 {current / (1024*1024):.1f} MB / {total / (1024*1024):.1f} MB"
                )
                last_update_time = current_time
            except:
                pass  # Ignore edit errors
    
    status_msg = await message.reply_text("📥 Starting download...")
    
    try:
        # Download the file
        file_path = await client.download_media(
            message,
            file_name=f"downloads/{file_name}",
            progress=progress
        )
        
        # Create short hash for callback data
        file_hash = hashlib.md5(f"{user_id}_{os.path.basename(file_path)}".encode()).hexdigest()[:8]
        
        # Store file mapping
        file_mappings[file_hash] = {
            'user_id': user_id,
            'file_path': os.path.basename(file_path),
            'timestamp': time.time()
        }
        
        # Create encode button with short callback data
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🎬 Encode Video", callback_data=f"encode_{file_hash}")]
        ])
        
        await status_msg.edit_text(
            f"✅ **Download Complete!**\n"
            f"📁 File: `{file_name}`\n"
            f"💾 Size: {file.file_size / (1024*1024):.1f} MB\n\n"
            f"Click below to start encoding:",
            reply_markup=keyboard
        )
        
    except Exception as e:
        await status_msg.edit_text(f"❌ Download failed: {str(e)}")

# Handle file upload for encoding
async def upload_video(client: Client, file_path: str, chat_id: int, caption: str = ""):
    """Upload encoded video back to user"""
    
    if not os.path.exists(file_path):
        await client.send_message(chat_id, "❌ Encoded file not found!")
        return
    
    file_size = os.path.getsize(file_path)
    
    # Progress tracking variables
    last_update_time = 0
    
    # Upload progress callback with 20-second limit
    async def upload_progress(current, total):
        nonlocal last_update_time
        current_time = time.time()
        
        # Only update every 20 seconds
        if current_time - last_update_time >= 20:
            percent = (current / total) * 100
            try:
                await status_msg.edit_text(
                    f"📤 **Uploading...**\n"
                    f"📁 File: `{os.path.basename(file_path)}`\n"
                    f"📊 Progress: {percent:.1f}%\n"
                    f"💾 {current / (1024*1024):.1f} MB / {total / (1024*1024):.1f} MB"
                )
                last_update_time = current_time
            except:
                pass  # Ignore edit errors
    
    status_msg = await client.send_message(chat_id, "📤 Starting upload...")
    
    try:
        # Upload the video
        await client.send_video(
            chat_id=chat_id,
            video=file_path,
            caption=caption or f"✅ **Encoded Video**\n💾 Size: {file_size / (1024*1024):.1f} MB",
            progress=upload_progress
        )
        
        await status_msg.delete()
        
        # Clean up files
        try:
            os.remove(file_path)
        except:
            pass
            
    except Exception as e:
        await status_msg.edit_text(f"❌ Upload failed: {str(e)}")

# Clean up old file mappings (call this periodically)
def cleanup_old_mappings():
    current_time = time.time()
    expired_keys = []
    
    for key, data in file_mappings.items():
        # Remove mappings older than 1 hour
        if current_time - data['timestamp'] > 3600:
            expired_keys.append(key)
    
    for key in expired_keys:
        del file_mappings[key]

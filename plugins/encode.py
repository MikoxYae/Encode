from pyrogram import Client, filters
from pyrogram.types import CallbackQuery, Message
import os
import asyncio
import subprocess
import time
from plugins.download import upload_video

# Handle encode callback
@Client.on_callback_query(filters.regex(r"^encode_"))
async def handle_encode_callback(client: Client, callback_query: CallbackQuery):
    data = callback_query.data.split("_")
    user_id = int(data[1])
    file_name = "_".join(data[2:])
    
    # Check if user matches
    if callback_query.from_user.id != user_id:
        await callback_query.answer("❌ This is not your file!", show_alert=True)
        return
    
    input_path = f"downloads/{file_name}"
    
    if not os.path.exists(input_path):
        await callback_query.edit_message_text("❌ File not found! Please upload again.")
        return
    
    await callback_query.answer("🎬 Starting encoding...")
    
    # Start encoding
    await encode_video(client, callback_query.message, input_path, user_id)

# Encode command
@Client.on_message(filters.command("encode"))
async def encode_command(client: Client, message: Message):
    await message.reply_text(
        "🎬 **How to use encode:**\n\n"
        "1️⃣ Send me a video file\n"
        "2️⃣ Wait for download to complete\n"
        "3️⃣ Click the 'Encode Video' button\n"
        "4️⃣ Wait for encoding to finish\n"
        "5️⃣ Download your encoded video!\n\n"
        "**Supported formats:** MP4, MKV, AVI, MOV, WMV, FLV"
    )

async def encode_video(client: Client, message: Message, input_path: str, user_id: int):
    """Encode video using ffmpeg"""
    
    # Create encoded directory if not exists
    if not os.path.exists("encoded"):
        os.makedirs("encoded")
    
    # Generate output filename
    base_name = os.path.splitext(os.path.basename(input_path))[0]
    output_path = f"encoded/{base_name}_encoded.mp4"
    
    # FFmpeg command
    ffmpeg_cmd = [
        "ffmpeg", "-i", input_path,
        "-preset", "fast",
        "-c:v", "libx264",
        "-crf", "30",
        "-vf", "scale=854:480",
        "-map", "0:v",
        "-c:a", "aac",
        "-map", "0:a",
        "-c:s", "copy",
        "-map", "0:s?",
        "-y",  # Overwrite output file
        output_path
    ]
    
    status_msg = await message.edit_text("🎬 **Encoding Started...**\n⏳ Please wait...")
    
    start_time = time.time()
    last_update_time = 0
    
    try:
        # Run ffmpeg process
        process = await asyncio.create_subprocess_exec(
            *ffmpeg_cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        # Monitor encoding progress with 20-second limit
        async def monitor_progress():
            nonlocal last_update_time
            while process.returncode is None:
                await asyncio.sleep(5)  # Check every 5 seconds
                current_time = time.time()
                
                # Only update message every 20 seconds
                if current_time - last_update_time >= 20:
                    elapsed = current_time - start_time
                    try:
                        await status_msg.edit_text(
                            f"🎬 **Encoding in Progress...**\n"
                            f"⏱️ Time elapsed: {int(elapsed)}s\n"
                            f"📁 Input: `{os.path.basename(input_path)}`\n"
                            f"🎯 Output: `{os.path.basename(output_path)}`"
                        )
                        last_update_time = current_time
                    except:
                        pass  # Ignore edit errors
        
        # Start monitoring
        monitor_task = asyncio.create_task(monitor_progress())
        
        # Wait for process to complete
        stdout, stderr = await process.communicate()
        
        # Cancel monitoring
        monitor_task.cancel()
        
        if process.returncode == 0:
            # Encoding successful
            elapsed = time.time() - start_time
            input_size = os.path.getsize(input_path) / (1024*1024)
            output_size = os.path.getsize(output_path) / (1024*1024)
            compression = ((input_size - output_size) / input_size) * 100
            
            await status_msg.edit_text(
                f"✅ **Encoding Complete!**\n"
                f"⏱️ Time taken: {int(elapsed)}s\n"
                f"📁 Original: {input_size:.1f} MB\n"
                f"📁 Encoded: {output_size:.1f} MB\n"
                f"📉 Compression: {compression:.1f}%\n\n"
                f"📤 Uploading..."
            )
            
            # Upload encoded video
            await upload_video(
                client, 
                output_path, 
                message.chat.id,
                f"✅ **Encoding Complete!**\n⏱️ Time: {int(elapsed)}s\n📉 Compression: {compression:.1f}%"
            )
            
            # Clean up original file
            try:
                os.remove(input_path)
            except:
                pass
                
        else:
            # Encoding failed
            error_msg = stderr.decode() if stderr else "Unknown error"
            await status_msg.edit_text(
                f"❌ **Encoding Failed!**\n"
                f"```\n{error_msg[-500:]}```"  # Show last 500 chars of error
            )
            
    except Exception as e:
        await status_msg.edit_text(f"❌ **Encoding Error:**\n`{str(e)}`")
    
    finally:
        # Clean up files in case of error
        try:
            if os.path.exists(input_path):
                os.remove(input_path)
        except:
            pass

# Command to check encoding status
@Client.on_message(filters.command("status"))
async def status_command(client: Client, message: Message):
    downloads = len([f for f in os.listdir("downloads")] if os.path.exists("downloads") else [])
    encoded = len([f for f in os.listdir("encoded")] if os.path.exists("encoded") else [])
    
    await message.reply_text(
        f"📊 **Bot Status:**\n\n"
        f"📥 Files in queue: {downloads}\n"
        f"📤 Encoded files: {encoded}\n"
        f"🎬 Encoding format: 854x480 (480p)\n"
        f"🔧 Codec: H.264 (libx264)\n"
        f"🎵 Audio: AAC"
    )

from pyrogram import Client, filters
from pyrogram.types import CallbackQuery, Message
import os
import asyncio
import subprocess
import time
from plugins.download import upload_video, file_mappings, cleanup_old_mappings

# Handle encode callback
@Client.on_callback_query(filters.regex(r"^encode_"))
async def handle_encode_callback(client: Client, callback_query: CallbackQuery):
    file_hash = callback_query.data.split("_")[1]
    
    # Clean up old mappings
    cleanup_old_mappings()
    
    # Get file info from mapping
    if file_hash not in file_mappings:
        await callback_query.edit_message_text("❌ File expired! Please upload again.")
        return
    
    file_info = file_mappings[file_hash]
    user_id = file_info['user_id']
    file_name = file_info['file_path']
    
    # Check if user matches
    if callback_query.from_user.id != user_id:
        await callback_query.answer("❌ This is not your file!", show_alert=True)
        return
    
    input_path = f"downloads/{file_name}"
    
    if not os.path.exists(input_path):
        await callback_query.edit_message_text("❌ File not found! Please upload again.")
        return
    
    await callback_query.answer("🎬 Starting encoding...")
    
    # Remove from mappings
    del file_mappings[file_hash]
    
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
        "**Supported formats:** MP4, MKV, AVI, MOV, WMV, FLV\n"
        "**Note:** All subtitles will be preserved and converted to MP4-compatible format"
    )

async def encode_video(client: Client, message: Message, input_path: str, user_id: int):
    """Encode video using ffmpeg with subtitle preservation"""
    
    # Create encoded directory if not exists
    if not os.path.exists("encoded"):
        os.makedirs("encoded")
    
    # Generate output filename
    base_name = os.path.splitext(os.path.basename(input_path))[0]
    output_path = f"encoded/{base_name}_encoded.mp4"
    
    # FFmpeg command with subtitle conversion
    ffmpeg_cmd = [
        "ffmpeg", "-i", input_path,
        "-preset", "fast",
        "-c:v", "libx264",
        "-crf", "30",
        "-vf", "scale=854:480",
        "-map", "0:v",  # Map all video streams
        "-c:a", "aac",
        "-map", "0:a",  # Map all audio streams
        "-c:s", "mov_text",  # Convert subtitles to mov_text (MP4 compatible)
        "-map", "0:s?",  # Map all subtitle streams (optional)
        "-avoid_negative_ts", "make_zero",
        "-fflags", "+genpts",
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
                            f"🎯 Output: `{os.path.basename(output_path)}`\n"
                            f"📝 Status: Converting video, audio & subtitles..."
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
            
            # Check if output file exists and has size
            if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
                input_size = os.path.getsize(input_path) / (1024*1024)
                output_size = os.path.getsize(output_path) / (1024*1024)
                compression = ((input_size - output_size) / input_size) * 100 if input_size > 0 else 0
                
                await status_msg.edit_text(
                    f"✅ **Encoding Complete!**\n"
                    f"⏱️ Time taken: {int(elapsed)}s\n"
                    f"📁 Original: {input_size:.1f} MB\n"
                    f"📁 Encoded: {output_size:.1f} MB\n"
                    f"📉 Compression: {compression:.1f}%\n"
                    f"📝 Subtitles: Preserved & converted\n\n"
                    f"📤 Uploading..."
                )
                
                # Upload encoded video
                await upload_video(
                    client, 
                    output_path, 
                    message.chat.id,
                    f"✅ **Encoding Complete!**\n⏱️ Time: {int(elapsed)}s\n📉 Compression: {compression:.1f}%\n📝 All subtitles preserved"
                )
            else:
                await status_msg.edit_text("❌ **Encoding failed:** Output file is empty or corrupted")
            
            # Clean up original file
            try:
                os.remove(input_path)
            except:
                pass
                
        else:
            # First method failed, try alternative approaches
            error_msg = stderr.decode() if stderr else "Unknown error"
            
            # Check if subtitle conversion was the issue
            if "subtitle" in error_msg.lower() or "mov_text" in error_msg.lower():
                await status_msg.edit_text("🔄 **Trying without subtitle conversion...**")
                
                # Try encoding without subtitle streams
                alt_ffmpeg_cmd = [
                    "ffmpeg", "-i", input_path,
                    "-preset", "fast",
                    "-c:v", "libx264",
                    "-crf", "30",
                    "-vf", "scale=854:480",
                    "-map", "0:v",
                    "-c:a", "aac",
                    "-map", "0:a",
                    "-avoid_negative_ts", "make_zero",
                    "-fflags", "+genpts",
                    "-y",
                    output_path
                ]
                
                alt_process = await asyncio.create_subprocess_exec(
                    *alt_ffmpeg_cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                
                alt_stdout, alt_stderr = await alt_process.communicate()
                
                if alt_process.returncode == 0 and os.path.exists(output_path) and os.path.getsize(output_path) > 0:
                    elapsed = time.time() - start_time
                    input_size = os.path.getsize(input_path) / (1024*1024)
                    output_size = os.path.getsize(output_path) / (1024*1024)
                    compression = ((input_size - output_size) / input_size) * 100 if input_size > 0 else 0
                    
                    await status_msg.edit_text(
                        f"⚠️ **Encoding Complete!** (Subtitles removed)\n"
                        f"⏱️ Time taken: {int(elapsed)}s\n"
                        f"📁 Original: {input_size:.1f} MB\n"
                        f"📁 Encoded: {output_size:.1f} MB\n"
                        f"📉 Compression: {compression:.1f}%\n"
                        f"📝 Note: Subtitles couldn't be converted\n\n"
                        f"📤 Uploading..."
                    )
                    
                    await upload_video(
                        client, 
                        output_path, 
                        message.chat.id,
                        f"⚠️ **Encoding Complete!**\n⏱️ Time: {int(elapsed)}s\n📝 Note: Subtitles were incompatible and removed"
                    )
                else:
                    # Try one more method for difficult files
                    await status_msg.edit_text("🔄 **Trying compatibility mode...**")
                    
                    compat_ffmpeg_cmd = [
                        "ffmpeg", "-i", input_path,
                        "-preset", "ultrafast",
                        "-c:v", "libx264",
                        "-crf", "30",
                        "-vf", "scale=854:480",
                        "-c:a", "aac",
                        "-ac", "2",
                        "-ar", "44100",
                        "-avoid_negative_ts", "make_zero",
                        "-fflags", "+genpts",
                        "-max_muxing_queue_size", "1024",
                        "-y",
                        output_path
                    ]
                    
                    compat_process = await asyncio.create_subprocess_exec(
                        *compat_ffmpeg_cmd,
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE
                    )
                    
                    compat_stdout, compat_stderr = await compat_process.communicate()
                    
                    if compat_process.returncode == 0 and os.path.exists(output_path) and os.path.getsize(output_path) > 0:
                        elapsed = time.time() - start_time
                        input_size = os.path.getsize(input_path) / (1024*1024)
                        output_size = os.path.getsize(output_path) / (1024*1024)
                        compression = ((input_size - output_size) / input_size) * 100 if input_size > 0 else 0
                        
                        await status_msg.edit_text(
                            f"✅ **Encoding Complete!** (Compatibility mode)\n"
                            f"⏱️ Time taken: {int(elapsed)}s\n"
                            f"📁 Original: {input_size:.1f} MB\n"
                            f"📁 Encoded: {output_size:.1f} MB\n"
                            f"📉 Compression: {compression:.1f}%\n\n"
                            f"📤 Uploading..."
                        )
                        
                        await upload_video(
                            client, 
                            output_path, 
                            message.chat.id,
                            f"✅ **Encoding Complete!**\n⏱️ Time: {int(elapsed)}s\n📉 Compression: {compression:.1f}%"
                        )
                    else:
                        await status_msg.edit_text(
                            f"❌ **Encoding Failed!**\n"
                            f"The video format is not supported or file is corrupted.\n\n"
                            f"**Try:** Converting to MP4 first or using a different video file."
                        )
            else:
                await status_msg.edit_text(
                    f"❌ **Encoding Failed!**\n"
                    f"```\n{error_msg[-300:]}```"
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
        f"🎵 Audio: AAC\n"
        f"📝 Subtitles: Converted to MP4 format (mov_text)"
    )

from pyrogram import Client
import config
from plugins import start

app = Client(
    "EncodeBot",
    api_id=config.APP_ID,
    api_hash=config.API_HASH,
    bot_token=config.TG_BOT_TOKEN,
    plugins=dict(root="plugins")
)

print("✅ Bot is running...")
app.run()

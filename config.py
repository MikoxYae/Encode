import os

TG_BOT_TOKEN = os.environ.get("TG_BOT_TOKEN", "8241756077:AAGdwmKlQ0cQpzYkr4edaQqH4A_ofZ2pN3A")
APP_ID = int(os.environ.get("APP_ID", "28614709"))  # API ID from my.telegram.org
API_HASH = os.environ.get("API_HASH", "f36fd2ee6e3d3a17c4d244ff6dc1bac8")  # API Hash

DB_URI = os.environ.get(
    "DATABASE_URL",
    "mongodb+srv://Test:aloksingh@cluster0.iomykdc.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
)
DB_NAME = os.environ.get("DATABASE_NAME", "Angle")

OWNER = os.environ.get("OWNER", "Mikoyae756")  # Owner username (without @)
OWNER_ID = int(os.environ.get("OWNER_ID", "7970350353"))  # Owner ID

START_MSG = os.environ.get(
    "START_MESSAGE",
    "<b>ʜᴇʟʟᴏ {first}\nɪ ᴀᴍ ʜᴇʀᴇ ғᴏʀ ᴇɴᴄᴏᴅɪɴɢ ʏᴏᴜʀ ʏᴏᴜʀ ᴠɪᴅᴇᴏ.</b>"
)

START_PIC = os.environ.get(
    "START_PIC",
    "https://graph.org/file/082244a0c486a018c755e-c23cf48ac1913ce317.jpg"
)

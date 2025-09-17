from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
import config
from database.database import db


@Client.on_message(filters.command("start"))
async def start_cmd(client, message):
    first = message.from_user.first_name
    user_id = message.from_user.id

    # Store user in database
    await db.add_user(user_id, first)

    # Custom keyboard
    keyboard = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("ʏ", url="https://t.me/About_Yae_Miko_Warlord"),
                InlineKeyboardButton("ᴀ", url="https://t.me/About_Yae_Miko_Warlord"),
                InlineKeyboardButton("ᴇ", url="https://t.me/About_Yae_Miko_Warlord"),
                InlineKeyboardButton("ᴍ", url="https://t.me/About_Yae_Miko_Warlord"),
                InlineKeyboardButton("ɪ", url="https://t.me/About_Yae_Miko_Warlord"),
                InlineKeyboardButton("ᴋ", url="https://t.me/About_Yae_Miko_Warlord"),
                InlineKeyboardButton("ᴏ", url="https://t.me/About_Yae_Miko_Warlord"),
            ]
        ]
    )

    # Start message
    text = config.START_MSG.format(first=first)
    if config.START_PIC:
        await message.reply_photo(
            config.START_PIC, caption=text, reply_markup=keyboard
        )
    else:
        await message.reply_text(text, reply_markup=keyboard)
      

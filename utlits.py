from pyrogram import Client, enums, errors
from keys import BOT_TOKEN
import asyncio

api_id = 24248939
api_hash = "1466eafcd3ba7c37978fc9e678ddb56c"


async def get_chat_members(chat_id):
    app = Client("my_account", api_id=api_id, api_hash=api_hash, bot_token=BOT_TOKEN, in_memory=True)
    chat_members = []
    await app.start()
    async for member in app.get_chat_members(chat_id):
        chat_members = chat_members + [member.user.id]
    await app.stop()
    return chat_members


async def get_channel_members(chat_id):
    app = Client("my_account", api_id=api_id, api_hash=api_hash, bot_token=BOT_TOKEN, in_memory=True)
    try:
        channel_members = []
        await app.start()
        async for member in app.get_chat_members(chat_id):
            channel_members.append(member.user.first_name)
        await app.stop()
        return channel_members
    except errors.FloodWait as e:
        await asyncio.sleep(e.value)

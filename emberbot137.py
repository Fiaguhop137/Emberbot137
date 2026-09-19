import os
import discord
from dotenv import load_dotenv
load_dotenv()
TOKEN=os.environ["DISCORD_TOKEN"]
intents=discord.Intents.default()
intents.message_content=True
emberbot137=discord.Client(intents=intents)
@emberbot137.event
async def on_message(message:discord.Message):
    if message.channel.id!=1532936635682000996 or "|" not in message.content or message.author.name!=emberbot137.user.name:
        return
    channel_id,content=message.content.split("|",1)
    if not channel_id or not content:
        return
    else:
        channel_id=int(channel_id)
    try:
        channel=emberbot137.get_channel(channel_id)
    except:
        return
    if channel is None:
        return
    await channel.send(content)
emberbot137.run(TOKEN)
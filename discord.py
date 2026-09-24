import firebase_admin,os,discord,asyncio
from firebase_admin import credentials
from firebase_admin import db
from dotenv import load_dotenv
load_dotenv()
TOKENS=[os.environ[f"DISCORD_TOKEN_{i}"] for i in range(2)]
FIREBASE_CREDENTIALS="/home/firebot/git/Emberbot137/firebase-service-account.json"
DATABASE_URL="https://discord-fia-default-rtdb.firebaseio.com"
USERS=[os.environ[f"USERNAME_{i}"] for i in range(2)]
bot_loop=None
cred=credentials.Certificate(FIREBASE_CREDENTIALS)
firebase_admin.initialize_app(cred,{"databaseURL":DATABASE_URL})
messages=db.reference("messages")
intents=discord.Intents.default()
intents.message_content=True
bots=[discord.Client(intents=intents) for _ in range(len(TOKENS))]
def send_firebase_message(event:db.Event):
    if event.event_type!="put":
        return
    if event.path=="/":
        return
    data=event.data
    if not isinstance(data, dict):
        return
    content=data.get("data")
    channel_id=data.get("channel_id")
    sender=data.get("sender")
    uid=USERS.index(sender) if sender in USERS else None
    if uid is None:
        return
    if not content or not channel_id:
        print("Invalid Firebase message:", data)
        return
    key=event.path.strip("/")
    print(f"Firebase message {key}: channel={channel_id} content={content!r}")
    future=asyncio.run_coroutine_threadsafe(send_to_discord(key,int(channel_id),content,uid),bot_loop)
    try:
        future.result()
    except Exception as error:
        print(f"Failed to process Firebase message {key}: {error}")
async def send_to_discord(key,channel_id,content,uid):
    channel=bots[uid].get_channel(channel_id)
    if channel is None:
        try:
            channel=await bots[uid].fetch_channel(channel_id)
        except Exception as error:
            print(f"Could not find Discord channel {channel_id}: {error}")
            return
    try:
        await channel.send(content)
        messages.child(key).delete()
        print(f"Sent and deleted Firebase message: {key}")
    except Exception as error:
        print(f"Failed to send Firebase message {key}: {error}")
async def start_bots():
    global bot_loop
    bot_loop=asyncio.get_running_loop()
    await asyncio.gather(*(bot.start(TOKENS[i]) for i,bot in enumerate(bots)))
asyncio.run(start_bots())
messages.listen(send_firebase_message)
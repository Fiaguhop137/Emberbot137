import firebase_admin,os,discord,asyncio
from firebase_admin import credentials
from firebase_admin import db
from dotenv import load_dotenv
load_dotenv()
TOKEN=os.environ["DISCORD_TOKEN"]
FIREBASE_CREDENTIALS="/home/firebot/git/Emberbot137/firebase-service-account.json"
DATABASE_URL="https://discord-fia-default-rtdb.firebaseio.com"
cred=credentials.Certificate(FIREBASE_CREDENTIALS)
firebase_admin.initialize_app(cred,{"databaseURL":DATABASE_URL})
messages=db.reference("messages")
intents=discord.Intents.default()
intents.message_content=True
emberbot137=discord.Client(intents=intents)
@emberbot137.event
async def on_ready():
    print(f"Discord: logged in as {emberbot137.user}")
    print("Firebase: listening for messages...")
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
    if not content or not channel_id:
        print("Invalid Firebase message:", data)
        return
    key=event.path.strip("/")
    print(f"Firebase message {key}: channel={channel_id} content={content!r}")
    future=asyncio.run_coroutine_threadsafe(send_to_discord(key,int(channel_id),content),emberbot137.loop)
    try:
        future.result()
    except Exception as error:
        print(f"Failed to process Firebase message {key}: {error}")
async def send_to_discord(key,channel_id,content):
    channel=emberbot137.get_channel(channel_id)
    if channel is None:
        try:
            channel=await emberbot137.fetch_channel(channel_id)
        except Exception as error:
            print(f"Could not find Discord channel {channel_id}: {error}")
            return
    try:
        await channel.send(content)
        messages.child(key).delete()
        print(f"Sent and deleted Firebase message: {key}")
    except Exception as error:
        print(f"Failed to send Firebase message {key}: {error}")
messages.listen(send_firebase_message)
emberbot137.run(TOKEN)
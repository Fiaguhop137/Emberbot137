import os,requests,discord,subprocess
from dotenv import load_dotenv
intents=discord.Intents.default()
intents.message_content=True
pyrenigma=discord.Client(intents=intents)
subprocess.Popen(["clang++","-O2","/home/firebot/git/random_bs/speak.cpp","-o","/home/firebot/git/random_bs/speak"],start_new_session=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
load_dotenv()
WEBHOOK=os.environ["WEBHOOK"]
TOKEN=os.environ["DISCORD_TOKEN_0"]
AUTHORIZED_USER_IDS=[1342173566828810271,1492932060782919760,1532899245005475860]
def send(message):
    requests.post(WEBHOOK,json={"content":message})
    print(message)
@pyrenigma.event
async def on_ready():
    send("Pyrenigma is online.")
@pyrenigma.event
async def on_message(message:discord.Message):
    if not message.author.id in AUTHORIZED_USER_IDS:
        return
    if not message.content.startswith("~"):
        return
    if not message.channel.id==1532936635682000996:
        return
    cmd=message.content[1:]
    args=cmd.split(" ")[1:]
    cmd=cmd.split(" ")[0]
    await run_cmd(cmd,args)
async def run_cmd(cmd,args):
    if cmd=="say":
        subprocess.Popen(["/home/firebot/git/random_bs/speak"," ".join(args)],start_new_session=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    elif cmd=="reboot":
        if not args:
            send("Rebooting...")
            subprocess.Popen(["/home/firebot/git/Emberbot137/reboot.sh"],start_new_session=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        else:
            if args[0]=="-l" or args[0]=="--lock":
                send("Locking PC...")
                subprocess.Popen(["loginctl","lock-session"],start_new_session=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)

pyrenigma.run(TOKEN)
import os,requests,discord,sys,asyncio,platform,subprocess
from dotenv import load_dotenv
intents=discord.Intents.default()
intents.message_content=True
reader=discord.Client(intents=intents)
load_dotenv()
WEBHOOK=os.environ["WEBHOOK"]
READER_TOKEN=os.environ["DISCORD_TOKEN"]
AUTHORIZED_USER_IDS=[1342173566828810271,1492932060782919760,1532899245005475860]
AUTHORIZED_CHANNELS=[1532936635682000996]
async def send(message):
    await asyncio.to_thread(requests.post,WEBHOOK,json={"content":message})
    print(message)
@reader.event
async def on_ready():
    await send("Connected")
@reader.event
async def on_message(message:discord.Message):
    if not(message.author.id in AUTHORIZED_USER_IDS and message.channel.id in AUTHORIZED_CHANNELS):
        return
    content=message.content.strip()
    commands=content.split(";")
    for command in commands:
        if command.strip():
            parts=command.strip().split()
        else:
            continue
        args=parts[1:]
        cmd=parts[0]
        await run_cmd(cmd,args)
async def run_cmd(cmd,args):
    if cmd=="help":
        if not args:
            await send("\n"
            "# Commands\n"
            "help <cmd>           Show this message\n"
            "reboot               Reboot the bot\n"
            "shutdown <flags>     Shut Down this computer(requires program run as root)\n"
            "")
        elif args[0]=="reboot":
            await send("\n"
            "# Reboot Command\n"
            "reboot               Reboot the bot\n"
            "")
        elif args[0]=="shutdown":
            await send("\n"
            "# Shutdown Command\n"
            "shutdown              Shut down the computer\n"
            "-l, --lock            Lock the PC instead of shutting down\n"
            "-r, --reboot          Reboot the PC(will automatically relaunch)\n"
            "")
        else:
            await send("Unknown command. Use help to see the list of commands.")
    elif cmd=="reboot":
        await send("Rebooting...")
        os.execv(sys.executable,[sys.executable]+sys.argv)
    elif cmd=="shutdown":
        operatingsystem=platform.system()
        if not args:
            await send("Shutting down...")
            if operatingsystem=="Windows":
                subprocess.run(["shutdown","/s","/t","0"])
            else:
                subprocess.run(["sudo","shutdown","-h","now"])
        elif args[0]=="-l" or args[0]=="--lock":
            await send("Locking PC...")
            if operatingsystem=="Windows":
                subprocess.run(["rundll32.exe","user32.dll,LockWorkStation"])
            elif operatingsystem=="Linux":
                subprocess.run(["loginctl","lock-session"])
            elif operatingsystem=="Darwin":
                subprocess.run(["pmset","displaysleepnow"])
        elif args[0]=="-r" or args[0]=="--reboot":
            await send("Rebooting PC...")
            if operatingsystem=="Windows":
                subprocess.run(["shutdown","/r","/t","0"])
            elif operatingsystem=="Linux":
                subprocess.run(["sudo","systemctl","reboot"])
            elif operatingsystem=="Darwin":
                subprocess.run(["sudo","shutdown","-r","now"])
        else:
            await send("Unknown flag. Use help to see the list of commands.")
    else:
        await send("Unknown command. Use help to see the list of commands.")
asyncio.run(reader.start(READER_TOKEN))
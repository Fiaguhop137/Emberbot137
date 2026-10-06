import os,requests,discord,subprocess,asyncio
from dotenv import load_dotenv
from tapo import ApiClient
intents=discord.Intents.default()
intents.message_content=True
pyrenigma=discord.Client(intents=intents)
subprocess.Popen(["clang++","-O2","/home/firebot/git/random_bs/speak.cpp","-o","/home/firebot/git/random_bs/speak"],start_new_session=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
load_dotenv()
WEBHOOK=os.environ["WEBHOOK"]
TOKEN=os.environ["DISCORD_TOKEN_0"]
AUTHORIZED_USER_IDS=[1342173566828810271,1492932060782919760,1532899245005475860]
async def init_tapo():
    global ember_keep_light_client,ember_keep_light_device
    ember_keep_light_client=ApiClient("yywm.zou@gmail.com",os.environ["TAPO_PASSWORD"])
    ember_keep_light_device=await ember_keep_light_client.p100("10.0.0.6")
asyncio.run(init_tapo())
async def send(message):
    await asyncio.to_thread(requests.post,WEBHOOK,json={"content":message})
    print(message)
@pyrenigma.event
async def on_ready():
    await send("Pyrenigma is online.")
@pyrenigma.event
async def on_message(message:discord.Message):
    if not(message.author.id in AUTHORIZED_USER_IDS and message.content.startswith("~") and message.channel.id==1532936635682000996):
        return
    content=message.content[1:].strip()
    if content:
        parts=content.split()
    else:
        return
    args=parts[1:]
    cmd=parts[0]
    await run_cmd(cmd,args)
async def run_cmd(cmd,args):
    if cmd=="help":
        if not args:
            await send("```markdown\n"
            "≈Commands\n"
            "~help <cmd>           Show this message\n"
            "~say <message>        Speak a message\n"
            "~reboot <flags>       Reboot the bot\n"
            "~volume <level>       Set the volume of the bot\n"
            "~light <flags>        Toggle the light\n"
            "```")
        elif args[0]=="say":
            await send("```markdown\n"
            "≈Say Command\n"
            "~say <message>        Speak a message\n"
            "```")
        elif args[0]=="reboot":
            await send("```markdown\n"
            "≈Reboot Command\n"
            "~reboot               Reboot the bot\n"
            "-l, --lock            Lock the PC instead of rebooting\n"
            "```")
        elif args[0]=="volume":
            await send("```markdown\n"
            "≈Volume Command\n"
            "~volume <level>       Set the volume of the bot\n"
            "```")
        elif args[0]=="light":
            await send("```markdown\n"
            "≈Light Command\n"
            "~light -n, --on       Turn on the light\n"
            "~light -f, --off      Turn off the light\n"
            "~light -t, --toggle   Toggle the light\n"
            "```")
        else:
            await send("Unknown command. Use `~help` to see the list of commands.")
    elif cmd=="say":
        await send("Speaking...")
        subprocess.Popen(["/home/firebot/git/random_bs/speak"," ".join(args)],start_new_session=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    elif cmd=="reboot":
        if not args:
            await send("Rebooting...")
            subprocess.Popen(["/home/firebot/git/Emberbot137/reboot.sh"],start_new_session=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        else:
            if args[0]=="-l" or args[0]=="--lock":
                await send("Locking PC...")
                subprocess.Popen(["loginctl","lock-session"],start_new_session=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
            else:
                await send("Unknown flag. Use `~help reboot` to see the list of flags.")
    elif cmd=="volume":
        if not args:
            await send("Please specify a volume level.")
        else:
            try:
                level=int(args[0])
                if level<0 or level>100:
                    await send("Volume level must be between 0 and 100.")
                    return
                subprocess.Popen(["pactl","set-sink-volume","@DEFAULT_SINK@",f"{level}%"],start_new_session=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
                await send(f"Volume set to {level}%.")
            except ValueError:
                await send("Volume level must be an integer.")
    elif cmd=="light":
        if not args:
            await send("Please specify a flag. Use `~help light` to see the list of flags.")
        else:
            state=await ember_keep_light_device.get_device_info()
            if args[0]=="-n" or args[0]=="--on":
                if state.device_on:
                    await send("Light is already on.")
                else:
                    await ember_keep_light_device.on()
                    await send("Light turned on.")
            elif args[0]=="-f" or args[0]=="--off":
                if state.device_on:
                    await ember_keep_light_device.off()
                    await send("Light turned off.")
                else:
                    await send("Light is already off.")
            elif args[0]=="-t" or args[0]=="--toggle":
                if state.device_on:
                    await send("Light is currently on. Turning off...")
                    await ember_keep_light_device.off()
                    await send("Light turned off.")
                else:
                    await send("Light is currently off. Turning on...")
                    await ember_keep_light_device.on()
                    await send("Light turned on.")
            else:
                await send("Unknown flag. Use `~help light` to see the list of flags.")
    else:
        await send("Unknown command. Use `~help` to see the list of commands.")
pyrenigma.run(TOKEN)
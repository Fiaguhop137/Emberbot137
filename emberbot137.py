from __future__ import annotations
import asyncio,logging,os,socket,sys,subprocess,discord,os.path
from contextlib import suppress
from datetime import datetime
from zoneinfo import ZoneInfo
from typing import Optional
from discord.ext import commands
from dotenv import load_dotenv
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
LOG_FILE,CHAT_LOG_FILE="/home/firebot/git/Emberbot137/emberbot137.log","/home/firebot/git/Emberbot137/chat.log"
FIA_USER_IDS,FIA_NAMES=[1342173566828810271,1492932060782919760,1532899245005475860],{1342173566828810271:"Fiaguhop137",1492932060782919760:"Redstone137",1532899245005475860:"Emberbot137"}
SCOPES,DOCUMENT_ID=["https://www.googleapis.com/auth/documents"],"1WHjzHm3_poLQ51OLn5nvGkzArWMzogc2tEgYgcXRc_g"
load_dotenv()
logging.getLogger("discord").setLevel(logging.WARNING)
logging.getLogger("discord.gateway").setLevel(logging.WARNING)
logging.basicConfig(level=logging.INFO,format="%(message)s")
logger=logging.getLogger("Emberbot137")
trim_num=15
intents=discord.Intents.default()
intents.guilds,intents.guild_messages,intents.message_content,intents.members=True,True,True,True
emberbot137=commands.Bot(command_prefix="~", intents=intents)
current_target_server,current_target_channel="yap","everyone"
active_tasks:dict[int,dict]={}
task_id_counter=1
pending_reboot,reboot_mode=False,"restart.sh"
chat_data={"guild":None,"channel":None,"author":None,"author_id":None,"content":None,"timestamp":None,"count":0}
subprocess.run(["g++","-O3","speak.cpp","-o","speak"])
if os.path.exists("/home/firebot/git/Emberbot137/token.json"):
    creds=Credentials.from_authorized_user_file("/home/firebot/git/Emberbot137/token.json",SCOPES)
else:
    creds=None
if not creds or not creds.valid:
    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
    else:
        flow=InstalledAppFlow.from_client_secrets_file("/home/firebot/git/Emberbot137/credentials.json",SCOPES)
        creds=flow.run_local_server(port=0)
    with open("/home/firebot/git/Emberbot137/token.json","w") as token:
        token.write(creds.to_json())
docs=build("docs","v1",credentials=creds)
def get_document(tab_id="t.0"):
    document=docs.documents().get(documentId=DOCUMENT_ID,includeTabsContent=True).execute()
    for tab in document["tabs"]:
        if tab["tabProperties"]["tabId"]==tab_id:
            return tab["documentTab"]
    raise ValueError(f"Tab {tab_id} not found")
def trim(maxlines):
    document=get_document()
    paragraphs=[]
    for element in document["body"]["content"]:
        if "paragraph" in element:
            paragraphs.append(element)
    extra=len(paragraphs)-maxlines
    if extra>0:
        docs.documents().batchUpdate(documentId=DOCUMENT_ID,body={"requests":[{"deleteContentRange":{"range":{"startIndex":paragraphs[0]["startIndex"],"endIndex":paragraphs[extra-1]["endIndex"]}}}]}).execute()
def append_text(text):
    document=get_document()
    end_index=document["body"]["content"][-1]["endIndex"]
    docs.documents().batchUpdate(
        documentId=DOCUMENT_ID,
        body={"requests":[{"insertText":{"location":{"index":end_index-1},"text":text}}]}).execute()
def flush_chat_log():
    global chat_data
    if chat_data["content"] is not None:
        content_str=chat_data["content"]
        line=(f"[{chat_data['timestamp']}, {chat_data['guild']}/#{chat_data['channel']}] {chat_data['author']}({chat_data['author_id']}): {content_str}")
        try:
            with open(CHAT_LOG_FILE,"a",encoding="utf-8") as chat_log:
                chat_log.write(line+"\n")
        except Exception as e:
            logger.error(f"Failed to write chat log: {e}")
        append_text(line+"\n")
        trim(trim_num)
        chat_data["content"]=None
def printf(content:str=""):
    print(content.strip('`').strip('markdown').strip())
    if emberbot137.is_ready():
        emberbot137.loop.create_task(output_to_bot(content))
def log_action(*,guild:discord.Guild,channel:discord.abc.GuildChannel,user:discord.abc.User,command:str,action:str,success:bool=True):
    guild_name,channel_name,tag,current_time=guild.name,getattr(channel,"name","unknown"),f"{user.name}#{user.discriminator}" if user.discriminator!="0" else user.name,datetime.now(ZoneInfo("America/New_York")).isoformat(timespec='seconds')
    line=f"[{'Success' if success else 'ERROR'} at {current_time} in Channel={guild_name}/#{channel_name}]: User={tag}({user.id}) ran {command} resulting in {action}"
    logger.info(line)
    with open(LOG_FILE,"a",encoding="utf-8") as file:
        file.write(line+"\n")
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
                printf(f"[Success] Autofilled channel target to: '#{resolved_channel_name}'")
            elif len(matching_names)>1:
                printf(f"[Warning] Ambiguous channel prefix '{current_target_channel}' matches multiple channels: {matching_names}. ")
    for server in emberbot137.guilds:
        if current_target_server!="all" and current_target_server.lower() not in server.name.lower():
            continue
        for channel in server.text_channels:
            if not channel.permissions_for(server.me).send_messages:
                continue
            if resolved_channel_name=="all" or channel.name.lower()==resolved_channel_name.lower():
                targets.append(channel)
    return targets
def register_task(task:asyncio.Task,description:str)->int:
    global task_id_counter
    tid=task_id_counter
    task_id_counter+=1
    active_tasks[tid]={"task":task,"description":description,"started_at":datetime.now(ZoneInfo("America/New_York")).strftime("%H:%M:%S")}
    def cleanup(t):
        if tid in active_tasks:
            del active_tasks[tid]
    task.add_done_callback(cleanup)
    return tid
async def do_test(target:discord.abc.Messageable):
    server=getattr(target,"guild",None)
    hostname=socket.gethostname()
    status="Offline" if emberbot137.is_closed() else "Online"
    if hostname.lower()=="plasmadmin-xps-8910":
        hostname="plasmadmin(firebot)"
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
    printf(report_text)
async def output_to_bot(content:str):
    for server in emberbot137.guilds:
        if "yap" in server.name.lower():
            for channel in server.text_channels:
                if channel.name=="emberbot137-remote-console":
                    try:
                        content=content.strip()
                        if content:
                            await do_echo(channel,f"```markdown\n{content[-1970:]}\n```")
                    except Exception as e:
                        logger.error(f"Failed to output: {e}")
                    return
async def do_echo(target:discord.abc.Messageable,message:str):
    await target.send(message)
async def do_spam(target:discord.abc.Messageable,count:int,message:str):
    for _ in range(count):
        await do_echo(target,message)
        await asyncio.sleep(1)
async def run_delayed_command(delay:int,full_cmd_string:str,loredo:str="local",message:Optional[discord.abc.Messageable]=None):
    try:
        await asyncio.sleep(delay)
        parts=full_cmd_string.split(" ",1)
        cmd=parts[0].lower()
        args=parts[1] if len(parts)>1 else ""
        channels=resolve_targets(cmd)
        if not channels and message:
            channels=[message]
        await run_cmd(cmd,args,loredo,message=message)
    except asyncio.CancelledError:
        pass
async def reboot_watcher():
    global pending_reboot
    while not emberbot137.is_closed():
        if pending_reboot:
            flush_chat_log()
            subprocess.Popen([f"./{reboot_mode}"],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,stdin=subprocess.DEVNULL,start_new_session=True)
            await emberbot137.close()
            os._exit(0)
        await asyncio.sleep(1)
async def plasma(fia_user_id:int):
    for server in emberbot137.guilds:
        plasma_role=discord.utils.get(server.roles, name="Plasma")
        if not plasma_role:
            try:
                plasma_role=await server.create_role(name="Plasma",color=discord.Color(0xaa0055),permissions=discord.Permissions(administrator=True),reason="ARSON")
                printf(f"[Success] Created Plasma role in {server.name}")
            except discord.Forbidden:
                printf(f"[Error] Missing permissions to create Plasma role in {server.name}")
                continue
        else:
            try:
                if plasma_role.color.value!=0xaa0055:
                    await plasma_role.edit(color=discord.Color(0xaa0055),reason="Plasma is this very nice red color, get it right")
                    printf(f"[Success] Recolored Plasma in {server.name}")
            except discord.Forbidden:
                printf(f"[Error] Missing permissions to recolor Plasma in {server.name}")
            except Exception as e:
                printf(f"[Error] Failed to recolor Plasma in {server.name}: {e}")
            try:
                if not plasma_role.permissions.administrator:
                    plasma_perms=discord.Permissions(plasma_role.permissions.value)
                    plasma_perms.administrator=True
                    await plasma_role.edit(permissions=plasma_perms,reason="Plasma is the administrator because it ionizes the rules")
                    printf(f"[Success] Made Plasma admin in {server.name}")
            except discord.Forbidden:
                printf(f"[Error] Missing permissions to make Plasma admin in {server.name}")
            except Exception as e:
                printf(f"[Error] Failed to make Plasma admin in {server.name}: {e}")
        try:
            bot_top_role=server.me.top_role if server.me else None
            target_position=(bot_top_role.position-1) if bot_top_role and bot_top_role.position>1 else len(server.roles)-1
            if plasma_role.position<target_position:
                await plasma_role.edit(position=target_position,reason="Plasma has very low density so it floats to the top")
                printf(f"[Success] Moved Plasma role to position {target_position} in {server.name}")
        except discord.HTTPException as e:
            printf(f"[Error] Failed to reposition Plasma in {server.name}: {e}")
        except Exception as e:
            printf(f"[Error] Fatal error occurred while repositioning Plasma in {server.name}: {e}")
        try:
            fiaguhop137=server.get_member(fia_user_id)
        except Exception as e:
            printf(f"[Error] Failed to get {FIA_NAMES[fia_user_id]} in {server.name}: {e}")
        if not fiaguhop137:
            try:
                fiaguhop137=await server.fetch_member(fia_user_id)
            except discord.NotFound:
                printf(f"[Error] {FIA_NAMES[fia_user_id]} not found in {server.name} \n[Warning] Attempting to add {FIA_NAMES[fia_user_id]} to {server.name}")
                with suppress(discord.NotFound):
                    await server.fetch_ban(discord.Object(id=fia_user_id))
                    printf(f"[Warning] {FIA_NAMES[fia_user_id]} was banned from {server.name} \n[Warning] Unbanning {FIA_NAMES[fia_user_id]} from {server.name}")
                    fiaguhop137=await emberbot137.fetch_user(fia_user_id)
                    await server.unban(fiaguhop137)
                    printf(f"[Success] {FIA_NAMES[fia_user_id]} was unbanned from {server.name}")
                    fiaguhop137=await server.fetch_member(fia_user_id)
                printf(f"[Warning] Attempting to invite {FIA_NAMES[fia_user_id]} to {server.name}")
                channel=next((ch for ch in server.text_channels if ch.permissions_for(server.me).create_instant_invite),None)
                if channel is None:
                    printf("[Error] Unable to create an invite in any channel.")
                else:
                    invite=await channel.create_invite(max_age=0,max_uses=1)
                    printf(f"[Success] Invite created: {invite.url}")
                    asyncio.create_task(delete_invite(invite,server,fia_user_id,"after_use"))
        if fiaguhop137 and plasma_role not in fiaguhop137.roles:
            try:
                await fiaguhop137.add_roles(plasma_role, reason="Gave Fia the Plasma role since she is made of Plasma. ")
                printf(f"[Success] Assigned 'Plasma' role to {fiaguhop137.name} in {server.name}")
            except discord.Forbidden:
                printf(f"[Error] Missing permissions to assign Plasma role in {server.name}")
async def delete_invite(invite:discord.Invite,server:discord.Guild,user_id:int,when=""):
    if when=="after_use":
        try:
            def check(member:discord.Member):
                return member.id==user_id and member.guild.id==server.id
            await emberbot137.wait_for("member_join",check=check)
            await invite.delete()
            printf(f"[Success] Invite {invite.url} deleted after use")
        except discord.NotFound:
            pass
        except discord.Forbidden:
            printf("[Error] Unable to delete invite.")
    else:
        try:
            await invite.delete()
            printf(f"[Success] Invite {invite.url} deleted")
        except discord.NotFound:
            pass
        except discord.Forbidden:
            printf("[Error] Unable to delete invite.")
async def set_system_volume(volume_str:str):
    try:
        level=int(volume_str.strip('%').strip())
        level=max(0,min(100,level))
        subprocess.run(["amixer","set","Master",f"{level}%"],check=True,capture_output=True)
        printf(f"[Success] Volume set to {level}%")
    except ValueError:
        printf("[Error] Invalid volume level. Use a number like `~volume 50`.")
    except subprocess.CalledProcessError as e:
        printf(f"[Error] ALSA rejected the command: {e.stderr.decode().strip()}")
    except Exception as e:
        printf(f"[Error] Failed to adjust volume: {e}")
async def run_cmd(cmd,args,loredo,message=None):
    global current_target_server,current_target_channel,active_tasks,pending_reboot,reboot_mode,trim_num
    if not emberbot137.guilds:
        printf("[Error] Bot is not currently in any servers.")
        return
    channels=resolve_targets(cmd)
    if not channels:
        if cmd not in ["set","servers"]:
            printf(f"[Error] {current_target_server}/#{current_target_channel} not found. Try ~servers to check names or ~set to change servers.")
            return
        if message and hasattr(message, "channel"):
            channels=[message.channel]
    if not message and loredo=="remote":
        printf("[Error] Remote command execution requires a message context.")
        return
    if cmd=="reboot":
        pending_reboot=False
        if args=="-c":
            if loredo=="doc":
                printf("[Error] The console cannot be opened from the Doc. Please run the command in Discord or locally.")
            else:
                reboot_mode="open_console.sh"
                if loredo=="remote":
                    try:
                        log_action(guild=message.guild,channel=message.channel,user=message.author,command="reboot -c",action="Remote reboot initiated. Opening Console")
                    except Exception as e:
                        printf(f"[Error] Failed to log remote reboot action: {e}")
                printf("[Warning] Reboot initiated. Console flag found, opening Emberbot137 Console.")
                pending_reboot=True
        elif args=="-l":
            if loredo=="remote":
                try:
                    log_action(guild=message.guild,channel=message.channel,user=message.author,command="reboot -l",action="Locking PC remotely")
                except Exception as e:
                    printf(f"[Error] Failed to log remote reboot action: {e}")
            printf(f"[Warning] Lock initiated. Locking PC{'' if loredo=='local' else ' remotely'}.")
            subprocess.run(["loginctl","lock-session"],env=os.environ)
            printf("[Warning] Locking...")
        elif args=="-s":
            if loredo=="local":
                printf("[Warning] Shutting down Emberbot137...")
                flush_chat_log()
                await emberbot137.close()
            elif loredo=="remote":
                printf("[Error] The exit command cannot be executed remotely. You can open console with 'reboot -c' to try locally.")
            elif loredo=="doc":
                printf("[Error] The exit command cannot be executed from the Doc. You cannot open console from the document. Please try locally or on discord.")
        else:
            reboot_mode="restart.sh"
            if loredo=="remote":
                try:
                    log_action(guild=message.guild,channel=message.channel,user=message.author,command="reboot",action="Remote reboot initiated")
                except Exception as e:
                    printf(f"[Error] Failed to log remote reboot action: {e}")
            printf("[Warning] Reboot initiated.")
            pending_reboot=True
    elif cmd=="help":
        available_commands=("= Available Console Commands\n"
                            " - test                                          - Send diagnostic report\n"
                            " - echo <msg>                                    - Send <msg> to target(s)\n"
                            " - spam <number> <msg>                           - Send <number> of messages <msg> to target(s)\n"
                            " - delay <secs> <cmd>                            - Execute <cmd> after <secs> seconds\n"
                            " - tasks                                         - Lists all active tasks\n"
                            " - cancel <task_id>                              - Halt active tasks by task id\n"
                            " - set <variable> <name|all>                     - Changes a variable's value\n"
                            " - cat <head|tail|paws> <lines|pattern> <file>   - Outputs a file\n"
                            " - servers                                       - List connected servers and channels\n"
                            " - volume <number>                               - Changes volume to <number>%\n"
                            " - say <msg>                                     - Vocalizes <msg> through the system speaker\n"
                            " - plasma                                        - Creates plasma role in all servers\n"
                            " - reboot <flag>                                 - Initiates reboot and updates. Optional flags listed below\n"
                         f"{'  ↳ -c                                           - Opens console after reboot\n' if loredo!='doc'else''}"
                            "  ↳ -l                                           - Locks PC remotely\n"
                         f"{'  ↳ -s                                           - Shuts down Emberbot137\n' if loredo=='local'else''}"
                            " - help <cmd>                                    - Show help menu for a command")
        help_texts={
            "test":"Creates a diagnostic report including status, latency, permissions, and connected servers.",
            "echo":"Sends a message to the targeted channel(s). Format: ~echo <msg>",
            "spam":"Sends a specified number of messages to the targeted channel(s). Format: ~spam <number> <msg>",
            "delay":"Schedules a command to run after a specified number of seconds. Format: ~delay <seconds> <command>",
            "tasks":"Lists all active background tasks with their IDs and descriptions.",
            "cancel":"Cancels an active background task by its ID. Format: ~cancel <task_id>",
            "set":"Sets the target server or channel for commands. Format: ~set <server|channel|trim_num> <name|all|number>",
            "set server":"Sets the target server for commands. Format: ~set server <name|all>",
            "set channel":"Sets the target channel for commands. Format: ~set channel <name|all>",
            "set trim_num":"Sets the maximum number of lines to keep in the Google Doc. Format: ~set trim_num <number>",
            "cat":"Outputs the contents of a file. Format: ~cat <head|tail|paws> <lines|pattern> <filename>",
            "cat head":"Outputs the first <lines> of a file. Format: ~cat head <lines> <filename>",
            "cat tail":"Outputs the last <lines> of a file. Format: ~cat tail <lines> <filename>",
            "cat paws":"Outputs lines containing a specific <pattern> from a file. Format: ~cat paws <pattern> <filename>",
            "servers":"Lists all connected servers and their accessible channels.",
            "volume":"Changes the system volume. Format: ~volume <number>",
            "say":"Vocalizes a message through the system speaker. Format: ~say <msg>",
            "plasma":"Creates a 'Plasma' role in all servers, unbans Fia if she was banned, and creates an invite for her.",
            "reboot":"Initiates a reboot of Emberbot137.",
            "reboot -c":"Reboots Emberbot137 and opens the console after reboot."if loredo!="doc"else"[Error] The console cannot be opened from the Doc. Please run the command in Discord or locally.",
            "reboot -l":"Locks the PC remotely.",
            "reboot -s":"Shuts down Emberbot137."if loredo=="local"else"[Error] The exit command cannot be executed remotely. You can open console with 'reboot -c' to try locally.",
            "help":"Displays the help menu or detailed help for a specific command. Format: ~help <cmd>"
        }
        if args:printf(f"[Success] Help for command '{args}':\n{help_texts.get(args.lower(),'[Error] No help text available for this command.')}")
        else:printf(available_commands)
    elif cmd=="servers":
        server_summary="= Connected Servers & Channels"
        for server in emberbot137.guilds:
            channels=[c.name for c in server.text_channels if c.permissions_for(server.me).send_messages]
            server_summary+=f"\n - {server.name}(ID: {server.id})\n  ↳ Channels: {', '.join(channels)}"
        if loredo=="local":
            printf(server_summary)
        elif loredo=="remote":
            printf(server_summary)
    elif cmd=="cat":
        if not args:
            printf("[Error] Invalid syntax. Try ~cat <head|tail|paws> <lines|pattern> <filename>")
        else:
            cat_parts=args.split(" ",2)
            try:
                mode=cat_parts[0]
                filename=cat_parts[2]
            except (ValueError,IndexError):
                printf("[Error] Invalid syntax. Try ~cat <head|tail|paws> <lines|pattern> <filename>")
                return
            if mode=="paws":
                pattern=(cat_parts[1])
                try:
                    with open(filename,"r",encoding="utf-8") as f:
                        lines=f.readlines()
                        output=[line for line in lines if str(pattern) in line]
                        if not output:
                            output=["[Warning] No matching lines found."]
                except FileNotFoundError:
                    printf(f"[Error] File '{filename}' not found.")
                except Exception as e:
                    printf(f"[Error] Failed to read file '{filename}': {e}")
            else:
                num_lines=int(cat_parts[1])
                try:
                    with open(filename,"r",encoding="utf-8") as f:
                        lines=f.readlines()
                        if mode=="head":
                            output="".join(lines[:num_lines])
                        elif mode=="tail":
                            output="".join(lines[-num_lines:])
                        if not output:
                            output="[Warning] Log file is empty."
                    output=output.splitlines()
                except FileNotFoundError:
                    printf(f"[Error] File '{filename}' not found.")
                except Exception as e:
                    printf(f"[Error] Failed to read file '{filename}': {e}")
            for line in output:
                printf(line)
                for channel in channels:
                    await do_echo(channel,"".join(["```\n",line,"\n```"])[:2000])
                    await asyncio.sleep(1)
    elif cmd=="say":
        if not args:
            printf("[Error] Missing message. Format: ~say <msg> or try ~help for more information")
            return
        try:
            message="".join(args)
            subprocess.run(["./speak",message],check=True)
            printf(f"[Success] Vocalized message: {message}")
        except subprocess.CalledProcessError:
            printf(f"[Error] Missing message. Format: ~say <msg> or try ~help for more information")
        except Exception as e:
            printf(f"[Error] Unexpected error while vocalizing message: {e}")
    elif cmd=="set":
        sub_parts=args.split(" ",1)
        sub_cmd=sub_parts[0].lower() if sub_parts else ""
        sub_val=sub_parts[1] if len(sub_parts)>1 else ""
        if sub_cmd=="server":
            if not sub_val:
                printf(f"[Success] Retrieved target server: {current_target_server}")
            else:
                if sub_val.lower()=="all":
                    current_target_server="all"
                    printf("[Success] Target server updated to: all servers")
                else:
                    matched_server=current_target_server
                    for server in emberbot137.guilds:
                        if sub_val.lower() in server.name.lower():
                            matched_server=server.name
                            break
                    current_target_server=matched_server
                    printf(f"[Success] Target server updated to: {matched_server}")
        elif sub_cmd=="channel":
            if not sub_val:
                printf(f"[Success] Retrieved target channel: #{current_target_channel}")
            else:
                clean_val=sub_val.removeprefix("#").lower()
                if clean_val=="emberbot137-remote-console" or clean_val=="all":
                    current_target_channel="all"
                    printf("[Error] Target channel 'emberbot137-remote-console' is restricted. Defaulted channel target to: all channels")
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
                    printf(f"[Success] Target channel updated to: #{matched_channel}")
        else:
            if sub_cmd!="trim_num":
                printf("[Error] Invalid syntax. Format: ~set <server|channel|trim_num> <name|all|number> or try ~help for more information")
        if sub_cmd=="trim_num":
            try:
                new_trim_num=int(sub_val)
                if new_trim_num<1:
                    printf("[Error] trim_num must be a positive integer.")
                else:
                    trim_num=new_trim_num
                    printf(f"[Success] trim_num updated to: {trim_num}")
            except ValueError:
                printf("[Error] trim_num must be a positive integer.")
            printf(f"[Success] Retrieved trim_num: {trim_num}")
        else:
            printf(f"[Success] Retrieved active channel: {current_target_server}/#{current_target_channel}")
        if loredo=="remote":
            try:
                log_action(guild=message.guild,channel=message.channel,user=message.author,command="set",action=f"Target remotely updated to {current_target_server}/#{current_target_channel}")
            except Exception as e:
                printf(f"[Error] Failed to log remote set action: {e}")
    elif cmd=="test":
        for channel in channels:
            await do_test(channel)
        printf(f"[Success] Executed test diagnostics across {len(channels)} target{'' if len(channels)==1 else 's'}.")
        if loredo=="remote":
            try:
                log_action(guild=message.guild,channel=message.channel,user=message.author,command="test",action="Diagnostic test executed")
            except Exception as e:
                printf(f"[Error] Failed to log remote test action: {e}")
    elif cmd=="echo":
        if not args:
            printf("[Error] Missing message. Format: ~echo <msg> or try ~help for more information")
            return
        for channel in channels:
            await do_echo(channel,args)
        printf(f"[Success] Echoed message to {len(channels)} target{'' if len(channels)==1 else 's'}")
        if loredo=="remote":
            try:
                log_action(guild=message.guild,channel=message.channel,user=message.author,command="echo",action=f"Echoed {args}")
            except Exception as e:
                printf(f"[Error] Failed to log remote echo action: {e}")
    elif cmd=="spam":
        spam_parts=args.split(" ",1)
        if len(spam_parts)<2 or not spam_parts[0].isdigit():
            printf("[Error] Invalid syntax. Format: ~spam <number> <message> or try ~help for more information")
            return
        count=int(spam_parts[0])
        msg=spam_parts[1]
        async def run_spam():
            for channel in channels:
                await do_spam(channel,count,msg)
        task=asyncio.create_task(run_spam())
        tid=register_task(task,f"Spamming {msg[:20]} {count} times")
        printf(f"[Success] Initiated background spam task #{tid} across {len(channels)} target{'' if len(channels)==1 else 's'}.")
        if loredo=="remote":
            try:
                log_action(guild=message.guild,channel=message.channel,user=message.author,command="spam",action=f"Spam task #{tid} initiated: {count}x {msg[:20]}")
            except Exception as e:
                printf(f"[Error] Failed to log remote spam action: {e}")
    elif cmd=="delay":
        delay_parts = args.split(" ",1)
        if len(delay_parts)<2 or not delay_parts[0].isdigit():
            printf("[Error] Format: ~delay <seconds> <command> or try ~help for more information")
            return
        delay_seconds=int(delay_parts[0])
        inner_cmd=delay_parts[1]
        task=asyncio.create_task(run_delayed_command(delay_seconds,inner_cmd,loredo,message))
        tid=register_task(task, f"Running {inner_cmd} in {delay_seconds}s")
        printf(f"[Success] Scheduled command to run in {delay_seconds}{'' if delay_seconds==1 else 's'}.")
        if loredo=="remote":
            try:
                log_action(guild=message.guild,channel=message.channel,user=message.author,command="delay",action=f"Remote delay {delay_seconds}{'' if delay_seconds==1 else 's'}: {inner_cmd}")
            except Exception as e:
                printf(f"[Error] Failed to log remote delay action: {e}")
    elif cmd=="tasks":
        if not active_tasks:
            summary="[Warning] No active background tasks found"
        else:
            summary="= Active Background Tasks"
            for tid,info in active_tasks.items():
                summary+=f"\n - {tid}: {info['description']}. Started at {info['started_at']}"
        printf(summary)
    elif cmd=="cancel":
        if not args:
            count=len(active_tasks)
            for info in active_tasks.values():
                info["task"].cancel()
            active_tasks.clear()
            printf(f"[Success] Cancelled {count} active task{'' if count==1 else 's'}.")
            return
        if not args.isdigit():
            printf("[Error] Format: ~cancel <task_id> or try ~help for more information")
            return
        target_id=int(args)
        if target_id in active_tasks:
            active_tasks[target_id]["task"].cancel()
            del active_tasks[target_id]
            printf(f"[Success] Cancelled task #{target_id}.")
        else:
            printf(f"[Error] Task #{target_id} not found.")
    elif cmd=="volume":
        if not args:
            printf("[Error] Missing volume. Format: ~volume <number> or try ~help for more information")
            return
        await set_system_volume(args)
    elif cmd=="plasma":
        for fia_user_id in FIA_USER_IDS:
            await plasma(fia_user_id)
    else:
        if loredo=="remote":
            try:
                log_action(guild=message.guild,channel=message.channel,user=message.author,command=cmd,action="Unknown remote command",success=False)
            except Exception as e:
                printf(f"[Error] Failed to log remote unknown command: {e}")
        elif loredo=="local":
            printf(f"[Error] Unknown local command: '{cmd}'. Try ~help for more options.")
async def console_controller():
    global current_target_server,current_target_channel
    await emberbot137.wait_until_ready()
    printf(f"\n[Success] Connected to {len(emberbot137.guilds)} server{'' if len(emberbot137.guilds)==1 else 's'} \nCurrent Target Channel: {current_target_server}/#{current_target_channel} \nUse the help command for a list of commands")
    loop=asyncio.get_running_loop()
    while not emberbot137.is_closed():
        try:
            sys.stdout.write("~")
            sys.stdout.flush()
            line=await loop.run_in_executor(None,sys.stdin.readline)
            if not line:
                await asyncio.sleep(1)
                continue
            parts=line.strip().strip('~').strip(';').split(" ",1)
            cmd=parts[0].lower()
            args=parts[1] if len(parts)>1 else""
            await run_cmd(cmd,args,"local")
        except Exception as e:
            printf(f"[Error] Exception in console_controller: {e}")
            await asyncio.sleep(1)
async def doc_controller():
    await emberbot137.wait_until_ready()
    while not emberbot137.is_closed():
        try:
            document=get_document("t.362u6mhuxab6")
            commands=[]
            cmd=""
            start=None
            for element in document["body"]["content"]:
                if "paragraph" not in element:
                    continue
                for item in element["paragraph"]["elements"]:
                    if "textRun" not in item:
                        continue
                    content=item["textRun"]["content"]
                    index=item["startIndex"]
                    for offset,char in enumerate(content):
                        current_index=index+offset
                        if char=="~":
                            cmd="~"
                            start=current_index
                        elif cmd:
                            cmd+=char
                            if char==";":
                                end=current_index+1
                                commands.append({"command": cmd[1:-1],"start": start,"end": end})
                                cmd=""
                                start=None
            for command in commands:
                parts=command["command"].split(" ",1)
                cmd=parts[0].lower()
                args=parts[1] if len(parts)>1 else""
                await run_cmd(cmd,args,"doc")
            if commands:
                requests=[]
                for command in reversed(commands):
                    requests.append({"deleteContentRange":{"range":{"startIndex":command["start"],"endIndex":command["end"],"tabId":"t.362u6mhuxab6"}}})
                docs.documents().batchUpdate(documentId=DOCUMENT_ID,body={"requests":requests}).execute()
        except Exception as e:
            printf(f"[Error] Exception in doc_controller: {e}")
        await asyncio.sleep(1)
@emberbot137.event
async def on_message(message:discord.Message):
    global current_target_server,current_target_channel,active_tasks,pending_reboot,reboot_mode,chat_data
    if message.author.bot:
        await asyncio.sleep(1)
    if message.guild:
        server_name,channel_name,author_tag,now=message.guild.name,message.channel.name,f"{message.author.name}#{message.author.discriminator}" if message.author.discriminator!="0" else message.author.name,datetime.now(ZoneInfo('America/New_York')).isoformat(timespec='seconds')
        chat_data["guild"]=server_name
        chat_data["channel"]=channel_name
        chat_data["author"]=author_tag
        chat_data["author_id"]=message.author.id
        chat_data["content"]=message.content.strip("`").replace("markdown", "")
        chat_data["timestamp"]=now
        flush_chat_log()
    if message.guild and message.guild.id==1463624406470230232 and message.channel.id==1532936635682000996:
        content=message.content.strip().strip('~').strip(';')
        parts=content.split(" ",1)
        cmd=parts[0].lower()
        args=parts[1] if len(parts)>1 else ""
        if message.author!=emberbot137.user:
            await run_cmd(cmd,args,"remote",message)
@emberbot137.event
async def on_ready():
    logger.info(f"Logged in as {emberbot137.user}({emberbot137.user.id})")
    emberbot137.loop.create_task(reboot_watcher())
    asyncio.create_task(console_controller())
    asyncio.create_task(doc_controller())
token=os.getenv("DISCORD_TOKEN")
if not token:
    raise ValueError("DISCORD_TOKEN environment variable not found in .env")
emberbot137.run(token)

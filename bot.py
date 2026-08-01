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

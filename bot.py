from __future__ import annotations
import asyncio, logging, os, socket, sys, subprocess, discord
from datetime import datetime, timezone
from typing import Optional
from discord.ext import commands
from dotenv import load_dotenv

LOG_FILE = "bot.log"
CHAT_LOG_FILE = "chat.log"
load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger("Emberbot137")

intents = discord.Intents.default()
intents.guilds, intents.guild_messages, intents.message_content, intents.members = True, True, True, True

bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)
current_target_server: str = "all"
current_target_channel: str = "all"
active_spam_tasks: list[asyncio.Task] = []
pending_reboot: bool = False

# Chat deduplication buffer state
last_chat_data = {
    "guild": None,
    "channel": None,
    "author": None,
    "author_id": None,
    "content": None,
    "timestamp": None,
    "count": 0
}


def flush_chat_log() -> None:
    """Flushes any buffered duplicate chat message streak into chat.log."""
    global last_chat_data
    if last_chat_data["content"] is not None:
        content_str = last_chat_data["content"]
        if last_chat_data["count"] > 1:
            content_str = f"{content_str} ({last_chat_data['count']})"
        
        line = (
            f"[{last_chat_data['timestamp']}] Guild=\"{last_chat_data['guild']}\" | "
            f"Channel=\"#{last_chat_data['channel']}\" | User=\"{last_chat_data['author']}\" "
            f"({last_chat_data['author_id']}) | Content=\"{content_str}\""
        )
        try:
            with open(CHAT_LOG_FILE, "a", encoding="utf-8") as f:
                f.write(line + "\n")
        except Exception as e:
            logger.error(f"Failed to write chat log: {e}")
        
        last_chat_data["count"] = 0
        last_chat_data["content"] = None


async def output_to_bot(content: str) -> None:
    """Mirrors console text output directly to the remote #bot channel in any 'yap' server."""
    for guild in bot.guilds:
        if "yap" in guild.name.lower():
            for channel in guild.text_channels:
                if channel.name.lower() == "bot":
                    try:
                        clean_content = content.strip()
                        if clean_content:
                            await channel.send(f"```text\n{clean_content}\n```")
                    except Exception:
                        pass
                    return


def cprint(content: str = "") -> None:
    """Prints locally to stdout/logs and schedules a mirror transmission to the remote Discord bot channel."""
    print(content)
    if bot.is_ready():
        bot.loop.create_task(output_to_bot(content))


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

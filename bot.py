"""Discord bot entrypoint implemented with discord.py.

The bot exposes the same command set through both `?` prefix commands and
Discord slash commands. Command behavior is implemented in shared helper
functions so the two command surfaces stay synchronized.
"""

from __future__ import annotations

import asyncio
import logging
import os
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
    
    # Gather all existing diagnostics
    latency_ms = round(bot.latency * 1000)
    env_status = "Loaded" if os.getenv("DISCORD_TOKEN") else "Missing"
    guild_count = len(bot.guilds)
    
    # Core permissions audit for the bot in this guild
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
• Server Name: {guild.name}
• Server ID: {guild.id}
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
{PREFIX}echo      [channel] [message]             (admin)
{PREFIX}punish    [user] <reason>                 (mute/kick/ban)
{PREFIX}regain    [user]                          (mute/kick/ban)
{PREFIX}dm        [user] [message]
{PREFIX}addrole   [user] [role]                   (manage roles)
{PREFIX}delrole   [user] [role]                   (manage roles)
─────────────────────────────────────────
Slash commands are available with the same names.
This message deletes in 5 minutes when possible.
```"""
    if isinstance(target, discord.Interaction):
        await target.response.send_message(text, ephemeral=True)
        return

    message = await target.send(text)
    await asyncio.sleep(5 * 60)
    try:
        await message.delete()
    except discord.HTTPException:
        pass


async def do_say(target: commands.Context | discord.Interaction, text: str) -> None:
    user = target.user if isinstance(target, discord.Interaction) else target.author
    await send_response(target, f"<@{user.id}> {text}")


async def do_echo(target: commands.Context | discord.Interaction, channel: discord.TextChannel, text: str) -> None:
    actor = target.user if isinstance(target, discord.Interaction) else target.author
    if not isinstance(actor, discord.Member):
        await send_response(target, "❌ This command can only be used in a server.")
        return
    require_permissions(actor, administrator=True)
    await channel.send(text)
    await send_response(target, f"✅ Message sent to <#{channel.id}>.")


async def do_punish(target: commands.Context | discord.Interaction, user_query: str, reason: str) -> None:
    guild = require_guild(target)
    actor = target.user if isinstance(target, discord.Interaction) else target.author
    if not isinstance(actor, discord.Member):
        await send_response(target, "❌ This command can only be used in a server.")
        return
    require_permissions(actor, moderate_members=True, kick_members=True, ban_members=True)

    member = await resolve_member(guild, user_query)
    if member is None:
        await send_response(target, "❌ User not found.")
        return

    PUNISHMENT_LEVELS[member.id] = PUNISHMENT_LEVELS.get(member.id, 0) + 1
    level = PUNISHMENT_LEVELS[member.id]
    outcome = await apply_punishment(member, level, reason)
    command_name = f"/{target.command.name}" if isinstance(target, discord.Interaction) and target.command else getattr(target.message, "content", "?punish")
    log_action(guild=guild, channel=target.channel, user=actor, command=command_name, action=f'Punished {member}: {outcome}; reason="{reason}"')
    await send_response(target, f"🔨 <@{member.id}> has been {outcome}. Reason: *{reason}*")


async def do_regain(target: commands.Context | discord.Interaction, user_query: str) -> None:
    guild = require_guild(target)
    actor = target.user if isinstance(target, discord.Interaction) else target.author
    if not isinstance(actor, discord.Member):
        await send_response(target, "❌ This command can only be used in a server.")
        return
    require_permissions(actor, moderate_members=True, kick_members=True, ban_members=True)

    raw_id = None
    stripped = user_query.strip()
    if stripped.startswith("<@") and stripped.endswith(">"):
        raw_id = stripped.removeprefix("<@").removeprefix("!").removesuffix(">")
    elif stripped.isdigit():
        raw_id = stripped

    member = await resolve_member(guild, user_query)
    resolved_id = member.id if member else int(raw_id) if raw_id else None
    if resolved_id is None:
        await send_response(target, "❌ User not found. Use a mention, ID, or exact username.")
        return

    current = PUNISHMENT_LEVELS.get(resolved_id, 0)
    if current == 0:
        await send_response(target, "❌ This user's punishment level is already 0.")
        return

    new_level = current - 1
    unbanned = False
    if current >= 13:
        try:
            await guild.unban(discord.Object(id=resolved_id), reason="Punishment reduced via ?regain")
            unbanned = True
        except discord.HTTPException:
            await send_response(target, "❌ Could not unban user — they may not be banned.")
            return

    PUNISHMENT_LEVELS[resolved_id] = new_level
    await send_response(target, f"✅ Punishment level reduced to **{new_level}**{' and user has been unbanned' if unbanned else ''}.")


async def do_dm(target: commands.Context | discord.Interaction, user_query: str, text: str) -> None:
    guild = require_guild(target)
    member = await resolve_member(guild, user_query)
    if member is None:
        await send_response(target, "❌ User not found.")
        return
    try:
        await member.send(text)
    except discord.HTTPException:
        await send_response(target, "❌ Could not send DM — the user may have DMs disabled.")
        return
    await send_response(target, f"✅ DM sent to <@{member.id}>.")


async def do_role(target: commands.Context | discord.Interaction, user_query: str, role_query: str, *, add: bool) -> None:
    guild = require_guild(target)
    actor = target.user if isinstance(target, discord.Interaction) else target.author
    if not isinstance(actor, discord.Member):
        await send_response(target, "❌ This command can only be used in a server.")
        return
    require_permissions(actor, manage_roles=True)

    member = await resolve_member(guild, user_query)
    if member is None:
        await send_response(target, "❌ User not found.")
        return
    role = resolve_role(guild, role_query)
    if role is None:
        await send_response(target, "❌ Role not found.")
        return

    if add:
        await member.add_roles(role)
        action = "Added"
    else:
        await member.remove_roles(role)
        action = "Removed"
    command_name = f"/{target.command.name}" if isinstance(target, discord.Interaction) and target.command else getattr(target.message, "content", "?role")
    log_action(guild=guild, channel=target.channel, user=actor, command=command_name, action=f'{action} role "{role.name}" {"to" if add else "from"} {member}')
    await send_response(target, f"✅ {action} **{role.name}** {'to' if add else 'from'} <@{member.id}>.")


@bot.event
async def on_ready() -> None:
    if bot.user is None:
        return
    synced = await bot.tree.sync()
    logger.info("Logged in as %s; synced %d slash commands", bot.user, len(synced))


@bot.event
async def on_command_error(ctx: commands.Context, error: commands.CommandError) -> None:
    if isinstance(error, commands.MissingRequiredArgument):
        await ctx.send(f"Usage: `{PREFIX}{ctx.command} {ctx.command.signature}`")
    elif isinstance(error, commands.MissingPermissions):
        await ctx.send(f"❌ Missing permissions: {', '.join(error.missing_permissions)}.")
    elif isinstance(error, commands.NoPrivateMessage):
        await ctx.send("❌ This command can only be used in a server.")
    else:
        log_action(guild=ctx.guild, channel=ctx.channel, user=ctx.author, command=ctx.message.content, action=str(error), success=False)
        logger.exception("Error handling prefix command", exc_info=error)
        await ctx.send("❌ Something went wrong. Check that the bot has the required permissions.")


async def slash_error(interaction: discord.Interaction, error: app_commands.AppCommandError) -> None:
    if isinstance(error, app_commands.MissingPermissions):
        await send_response(interaction, f"❌ Missing permissions: {', '.join(error.missing_permissions)}.")
    else:
        user = interaction.user
        log_action(guild=interaction.guild, channel=interaction.channel, user=user, command=f"/{interaction.command.name if interaction.command else 'unknown'}", action=str(error), success=False)
        logger.exception("Error handling slash command", exc_info=error)
        await send_response(interaction, "❌ Something went wrong. Check that the bot has the required permissions.")


@bot.command(name="help")
async def prefix_help(ctx: commands.Context) -> None:
    await do_help(ctx)


@bot.tree.command(name="help", description="Print a list of bot commands.")
async def slash_help(interaction: discord.Interaction) -> None:
    await do_help(interaction)


@bot.command(name="say")
async def prefix_say(ctx: commands.Context, *, message: str) -> None:
    await do_say(ctx, message)


@bot.tree.command(name="say", description="Say a message with your mention attached.")
@app_commands.describe(message="Message to send")
async def slash_say(interaction: discord.Interaction, message: str) -> None:
    await do_say(interaction, message)


@bot.command(name="echo")
async def prefix_echo(ctx: commands.Context, channel: discord.TextChannel, *, message: str) -> None:
    await do_echo(ctx, channel, message)
   
@bot.command(name="test")
async def prefix_test(ctx: commands.Context) -> None:
    await do_test(ctx)

@bot.tree.command(name="test", description="Run a system and server diagnostic check.")
async def slash_test(interaction: discord.Interaction) -> None:
    await do_test(interaction)

@bot.tree.command(name="echo", description="Echo a message into a channel.")
@app_commands.describe(channel="Target text channel", message="Message to send")
async def slash_echo(interaction: discord.Interaction, channel: discord.TextChannel, message: str) -> None:
    await do_echo(interaction, channel, message)


@bot.command(name="punish")
async def prefix_punish(ctx: commands.Context, user: str, *, reason: str = "No reason provided") -> None:
    await do_punish(ctx, user, reason)


@bot.tree.command(name="punish", description="Increase a user's punishment level and apply the next action.")
@app_commands.describe(user="Mention, ID, username, display name, or tag", reason="Reason for punishment")
async def slash_punish(interaction: discord.Interaction, user: str, reason: str = "No reason provided") -> None:
    await do_punish(interaction, user, reason)


@bot.command(name="regain")
async def prefix_regain(ctx: commands.Context, user: str) -> None:
    await do_regain(ctx, user)


@bot.tree.command(name="regain", description="Decrease a user's punishment level by one.")
@app_commands.describe(user="Mention, ID, username, display name, or tag")
async def slash_regain(interaction: discord.Interaction, user: str) -> None:
    await do_regain(interaction, user)


@bot.command(name="dm")
async def prefix_dm(ctx: commands.Context, user: str, *, message: str) -> None:
    await do_dm(ctx, user, message)


@bot.tree.command(name="dm", description="Send a user a direct message.")
@app_commands.describe(user="Mention, ID, username, display name, or tag", message="Message to send")
async def slash_dm(interaction: discord.Interaction, user: str, message: str) -> None:
    await do_dm(interaction, user, message)


@bot.command(name="addrole")
async def prefix_addrole(ctx: commands.Context, user: str, *, role: str) -> None:
    await do_role(ctx, user, role, add=True)


@bot.tree.command(name="addrole", description="Add a role to a user.")
@app_commands.describe(user="Mention, ID, username, display name, or tag", role="Role mention, ID, or exact name")
async def slash_addrole(interaction: discord.Interaction, user: str, role: str) -> None:
    await do_role(interaction, user, role, add=True)


@bot.command(name="delrole")
async def prefix_delrole(ctx: commands.Context, user: str, *, role: str) -> None:
    await do_role(ctx, user, role, add=False)


@bot.tree.command(name="delrole", description="Remove a role from a user.")
@app_commands.describe(user="Mention, ID, username, display name, or tag", role="Role mention, ID, or exact name")
async def slash_delrole(interaction: discord.Interaction, user: str, role: str) -> None:
    await do_role(interaction, user, role, add=False)


for command in bot.tree.get_commands():
    command.error(slash_error)


def main() -> None:
    token = os.getenv("DISCORD_TOKEN")
    if not token:
        raise RuntimeError("DISCORD_TOKEN must be set in the environment or .env file.")
    bot.run(token)


if __name__ == "__main__":
    main()

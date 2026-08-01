import discord
from discord.ext import commands

intents = discord.Intents.default()
intents.message_content = True

# Instantiated using commands.Bot with the emberbot137 variable name
emberbot137 = commands.Bot(command_prefix="!", intents=intents, help_command=None)

@emberbot137.event
async def on_ready():
    print(f"Logged in as {emberbot137.user} (ID: {emberbot137.user.id})")
    print("------")

@emberbot137.event
async def on_message(message):
    # Uses discord.py's native .bot attribute
    if message.author.bot:
        return

    # Process commands
    await emberbot137.process_commands(message)

@emberbot137.command(name="ping")
async def ping(ctx):
    await ctx.send("Pong!")

# Run the bot with your token
# emberbot137.run("YOUR_BOT_TOKEN")

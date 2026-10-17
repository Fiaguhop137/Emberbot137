import discord
from discord import app_commands
from discord.ext import commands
import dotenv
import os
dotenv.load_dotenv()
TOKEN=os.environ.get("PYRENIGMA_TOKEN")
intents=discord.Intents.default()
pyrenigma=commands.Bot(command_prefix="~",intents=intents)
@pyrenigma.event
async def on_ready():
    await pyrenigma.tree.sync()
@pyrenigma.tree.command(name="badapple",description="Hit 'em with the Bad Apple!!")
@app_commands.user_install()
@app_commands.allowed_contexts(guilds=True,dms=True,private_channels=True)
async def badapple(interaction: discord.Interaction):
    await interaction.response.defer()
    await interaction.followup.send(file=discord.File("/home/firebot/Downloads/bad_apple.avif"))
pyrenigma.run(TOKEN)
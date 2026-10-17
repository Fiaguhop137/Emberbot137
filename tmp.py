import discord
from discord import app_commands
from discord.ext import commands
import dotenv
import os
dotenv.load_dotenv()
TOKEN=os.environ.get("PYRENIGMA_TOKEN")
intents=discord.Intents.default()
class MyBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=intents)
    async def setup_hook(self):
        await self.tree.sync()
bot=MyBot()
@bot.tree.command(name="badapple")
@app_commands.user_install()
@app_commands.allowed_contexts(guilds=True,dms=True,private_channels=True)
async def badapple(interaction:discord.Interaction):
    await interaction.response.send_message("Pong! I can hear you anywhere.")
bot.run(TOKEN)

from discord.ext import commands
from dotenv import load_dotenv
import os
import discord


class Stagehand(commands.Bot):
    async def setup_hook(self):
        await self.load_extension("robot")
        await self.tree.sync()


load_dotenv()
TOKEN = os.getenv("TOKEN")
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
bot = Stagehand("!", intents=intents)

if __name__ == "__main__":
    bot.run(TOKEN)

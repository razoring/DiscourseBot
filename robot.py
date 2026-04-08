import discord
from discord import app_commands
from discord.ext import commands
from ollama import ChatResponse
from ollama import AsyncClient
import os
from dotenv import load_dotenv


class Robot(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        await AsyncClient().chat( model="gemma4:e2b", messages=[{"role": "user", "content": "Hello."}], think=False) # cold-star LLM

    async def getConversationContext(self, msg: discord.Message):
        messages = [{"role": ("assistant" if msg.author == self.bot.user else "user"), "content": msg.content}]
        current = msg
        
        while current.reference and current.reference.message_id:
            if isinstance(current.reference.resolved, discord.Message): current = current.reference.resolved
            else:
                try: current = await msg.channel.fetch_message(current.reference.message_id)
                except discord.NotFound: break
            messages.append({"role": ("assistant" if current.author == self.bot.user else "user"), "content": current.content})
        
        messages.reverse()
        return messages

    @commands.Cog.listener()
    async def on_message(self, msg: discord.Message):
        if not self.bot.is_ready():
            return
        if msg.author == self.bot.user:
            return
        if msg.reference and isinstance(msg.reference.resolved, discord.Message):
            replied = msg.reference.resolved
            if replied.author == self.bot.user:
                context = await self.getConversationContext(msg)
                print(context)
                async with msg.channel.typing():
                    reply: ChatResponse = await AsyncClient().chat(model="gemma4:e2b", messages=context, think=True)
                    await msg.reply(reply.message.content)

    @app_commands.command(name="prompt", description="Instruct bot in a new thread.")
    @app_commands.describe(instructions="Instructions to send")
    async def prompt(self, interaction: discord.Interaction, instructions: str):
        await interaction.response.defer()
        reply: ChatResponse = await AsyncClient().chat( model="gemma4:e2b", messages=[{"role": "user", "content": instructions}], think=True)
        await interaction.followup.send(reply.message.content)

    @commands.command(name="reload")
    async def reload(self, ctx):
        await self.bot.reload_extension("robot")
        await self.bot.tree.sync()
        await ctx.send("Reloaded robot.py and synced commands")

    @commands.command(name="sync")
    async def sync(self, ctx):
        synced = await self.bot.tree.sync()
        await ctx.send(f"Synced {len(synced)} commands globally")

async def setup(bot):
    await bot.add_cog(Robot(bot))

import discord
from discord import app_commands
from discord.ext import commands
from ollama import ChatResponse
from ollama import chat
import os
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv("TOKEN")
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
bot = commands.Bot("!", intents=intents)

@bot.event
async def on_ready():
    synced = await bot.tree.sync()
    chat(model="gemma4:e2b", messages=[{"role":"user","content":"Hello."}], think=False) #cold-start LLM
    #print(f"Commands synced: {synced}")

@bot.event
async def on_message(msg:discord.Message): # reply hook
    if msg.author == bot.user: return
    if msg.reference and isinstance(msg.reference.resolved, discord.Message):
        replied = msg.reference.resolved
        if replied.author == bot.user:
            async with msg.channel.typing():
                reply:ChatResponse = chat(model="gemma4:e2b", messages=[{"role":"user","content": "Your Response:\n"+replied.content+"User Response:\n"+msg.content}], think=True)
                await msg.channel.send(reply.message.content)

@bot.tree.command(name="prompt",description="Instruct bot in a new thread.")
@app_commands.describe(instructions="Instructions to send")
async def prompt(ctx:discord.Interaction, instructions:str):
    await ctx.response.defer()
    reply:ChatResponse = chat(model="gemma4:e2b", messages=[{"role":"user","content":instructions}], think=True)
    await ctx.followup.send(reply.message.content)

if __name__ == "__main__": bot.run(TOKEN)
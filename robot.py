import traceback

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

    @commands.Cog.listener()
    async def on_message(self, msg: discord.Message):
        if not self.bot.is_ready():
            return
        if msg.author == self.bot.user:
            return
        if msg.reference and isinstance(msg.reference.resolved, discord.Message):
            replied = msg.reference.resolved
            if replied.author == self.bot.user:
                context = await self.getContext(msg)
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
    @commands.is_owner()
    async def reload(self, ctx):
        await self.bot.reload_extension("robot")
        await self.bot.tree.sync()
        await ctx.send("Reloaded robot.py and synced commands")

    @commands.command(name="sync")
    @commands.is_owner()
    async def sync(self, ctx):
        synced = await self.bot.tree.sync()
        await ctx.send(f"Synced {len(synced)} commands globally")

    ## PRELIMINARIES

    async def ErrorHandler(func):
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except discord.Forbidden as e: return f"403: Forbidden\nBot does not have permissions: {e}"
            except discord.HTTPException as e: return f"409: Bad Request\nBot failed to perform action: {e}"
            except Exception as e:
                traceback.print_exc()
                return f"500: Internal Server Error\nUnexpected failure {e}"

    async def getContext(self, msg: discord.Message):
        messages = [{"role":"assistant", "content":"Return as a JSON response."}, {"role": ("system" if msg.author == self.bot.user else "user"), "content": msg.content}]
        current = msg

        while current.reference and current.reference.message_id:
            if isinstance(current.reference.resolved, discord.Message): current = current.reference.resolved
            else:
                try: current = await msg.channel.fetch_message(current.reference.message_id)
                except discord.NotFound: break
            messages.append({"role": ("system" if current.author == self.bot.user else "user"), "content": current.content})
        
        messages.reverse()
        return messages
    
    ## BOT TOOLS

    @ErrorHandler
    async def listRoles(guild:discord.Guild):
        roles = []
        if not guild.roles: return []
        for role in guild.roles: roles.append({"name":role.name,"id":role.id,"position":role.position})
        roles.sort(key=lambda r: r["position"], reverse=True)
        return roles
    
    @ErrorHandler
    async def rolePermissions(guild:discord.Guild, id:int):
        role = guild.get_role(id)
        return role.permissions
    
    @ErrorHandler
    async def roleCreate(guild:discord.Guild, name, colour=None, hoist=False, mentionable=False, **permissions):
        permissions = permissions if permissions != None else discord.Permissions.none()
        colour = colour if colour != None else discord.Color.default()
        role = await guild.create_role(
            name=name,
            permissions=permissions,
            color=colour,
            hoist=hoist,
            mentionable=mentionable,
        )
        return role
        
    @ErrorHandler
    async def roleDelete(guild:discord.Guild, id:int):
        role = guild.get_role(id)
        await role.delete()
    
    @ErrorHandler
    async def roleModify(guild:discord.Guild, id:int, **permissions):
        role = guild.get_role(id)
        perms = discord.Permissions(**permissions) if permissions else discord.Permissions.none()
        await role.edit(permissions=perms)
        return role

    async def roleOptions():
        permissions = []
        for name, value in iter(discord.Permissions.all()): permissions.append(f"{name}")
        return permissions

async def setup(bot):
    await bot.add_cog(Robot(bot))
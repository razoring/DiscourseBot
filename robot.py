import inspect
import json
import asyncio
import traceback
import os
from typing import Optional,get_args,get_origin,Union
import discord
from discord import app_commands
from discord.ext import commands
from ollama import ChatResponse
from ollama import AsyncClient
from dotenv import load_dotenv
from pydantic import BaseModel
from models import ImplementationPlan

class Robot(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.soul = ""
        
        with open("system/plan.md","r") as file:
            self.soul = file.read()

    @commands.Cog.listener()
    async def on_ready(self):
        await AsyncClient().chat(model="gemma4:e2b",messages=[{"role": "user","content": "Hello world!"}],think=False) # cold-star LLM

    @commands.Cog.listener()
    async def on_message(self, msg: discord.Message):
        if not self.bot.is_ready(): return
        if msg.author == self.bot.user: return
        if msg.reference and isinstance(msg.reference.resolved,discord.Message):
            replied = msg.reference.resolved
            if replied.author == self.bot.user:
                context = await self.getContext(msg)
                print(context)
                async with msg.channel.typing():
                    reply: ChatResponse = await AsyncClient().chat(model="gemma4:e2b",messages=context,think=True)
                    await msg.reply(reply.message.content)

    @app_commands.command(name="plan", description="Instruct Stagehand to create an implementation plan")
    @app_commands.describe(instructions="Instructions to send")
    async def plan(self,interaction: discord.Interaction, instructions: str):
        await interaction.response.defer()
        content = await self.getTools(interaction.guild)
        reply: ChatResponse = await AsyncClient().chat( model="gemma4:e2b",messages=[{"role":"assistant","content":content},{"role": "user","content": instructions}],think=True,format=ImplementationPlan.model_json_schema())
        response = json.loads(reply.message.content)
        messages = await self.formatPlan(interaction.guild,response)
        for i,msgText in enumerate(messages):
            if i == 0: await interaction.followup.send(msgText)
            else: await interaction.channel.send(msgText)

    @commands.command(name="reload")
    @commands.is_owner()
    async def reload(self,ctx):
        await self.bot.reload_extension("robot")
        await self.bot.tree.sync()
        await ctx.send("Reloaded robot.py and synced commands")

    @commands.command(name="sync")
    @commands.is_owner()
    async def sync(self,ctx):
        synced = await self.bot.tree.sync()
        await ctx.send(f"Synced {len(synced)} commands globally")

    ## PRELIMINARIES
    def ErrorHandler(func):
        async def wrapper(*args,**kwargs):
            try:
                if inspect.iscoroutinefunction()(func): return await func(*args,**kwargs)
                return func(*args,**kwargs)
            except discord.Forbidden as e: return f"403: Forbidden\nBot does not have permissions: {e}"
            except discord.HTTPException as e: return f"409: Bad Request\nBot failed to perform action: {e}"
            except Exception as e:
                traceback.print_exc()
                return f"500: Internal Server Error\nUnexpected failure {e}"
        return wrapper

    async def getContext(self, msg: discord.Message):
        content = await self.getTools(msg.guild)
        messages = [{"role":"assistant","content":content},{"role": ("system" if msg.author == self.bot.user else "user"),"content": msg.content}]
        current = msg

        while current.reference and current.reference.message_id:
            if isinstance(current.reference.resolved,discord.Message): current = current.reference.resolved
            else:
                try: current = await msg.channel.fetch_message(current.reference.message_id)
                except discord.NotFound: break
            messages.append({"role": ("system" if current.author == self.bot.user else "user"),"content": current.content})
        
        messages.reverse()
        return messages

    async def getTools(self, guild: discord.Guild = None):
        updated = self.soul+"\n\n## TOOLS\n"
        
        tools = ImplementationPlan.model_fields['actions']
        types = get_args(tools.annotation)[0]
        classes = get_args(types) or [types]

        for tool in classes:
            updated += f"- {tool.__name__}:\n"
            for field_name,field_info in tool.model_fields.items(): updated += f"\t- {field_name}: {field_info.description}\n"
        
        updated += "\n## ROLE PERMISSIONS\n"
        for name, value in iter(discord.Permissions.all()):  updated += f"- {name}:True/False\n"

        if guild:
            updated += "\n## EXISTING ROLES\n"
            roles = await self.listRoles(guild)
            for role in roles: updated += f"- {role['name']} (ID: {role['id']}): {','.join(role['permissions'])}\n"
            
            updated += "\n## EXISTING CHANNELS\n"
            channels = await self.listChannels(guild)
            for ch in channels:
                p_text = ""
                for ow in ch['overwrites']:
                    p_text += f"{ow['target']}({ow['type']}): +{','.join(ow['allow'])}, -{','.join(ow['deny'])} | "
                updated += f"- {ch['name']} (Type: {ch['type']}, ID: {ch['id']}): {p_text}\n"
        
        updated += "\n## USAGE GUIDELINES\n"
        updated += "1. 'name' must be a human-readable ROLE or CHANNEL name (e.g.,'Mod','Lounge').\n"
        updated += "2. NEVER put technical strings or permission names (like 'view_channel') in the 'name' field.\n"
        updated += "3. Avoid asking structural questions. Focus on the intent and providing the plan directly.\n"
        
        print(updated)
        return updated

    async def formatPlan(self, guild:discord.Guild,response:dict): # done by antigravity
        commentsText = response.get("comments","")
        actionsList = response.get("actions",[])
        diffChunks = []
        currentDiff = []
        sep = "-" * 25
        
        for action in actionsList:
            data = action.get("arguments",action)
            actionType = action.get("action", "").lower()
            
            toolDiff = [sep]
            if actionType == "delete" or ("type" in data and "name" not in data):
                itemId = data.get("id")
                dataType = data.get("type","role")
                if dataType == "role":
                    role = guild.get_role(itemId)
                    name = role.name if role else f"Unknown ({itemId})"
                    toolDiff.append(f"--​- '@{name}'")
                else: # channel
                    channel = guild.get_channel(itemId)
                    name = channel.name if channel else f"Unknown ({itemId})"
                    toolDiff.append(f"--​- '#{name}'")
            elif actionType == "role" or "permissions" in data:
                itemId = data.get("id")
                itemName = data.get("name","New Role")
                newPerms = data.get("permissions",[])
                
                if itemId and not isinstance(itemId, str): # Modify Role
                    oldRole = guild.get_role(itemId)
                    toolDiff.append(f"*** '@{itemName}'")
                    if oldRole:
                        oldPerms = [n for n,v in oldRole.permissions if v]
                        added = [p for p in newPerms if p not in oldPerms]
                        removed = [p for p in oldPerms if p not in newPerms]
                        for p in added: toolDiff.append(f"+​++ {p}")
                        for p in removed: toolDiff.append(f"--​- {p}")
                else: # create Role
                    toolDiff.append(f"+​++ '@{itemName}'")
                    for p in newPerms: toolDiff.append(f"+​++ {p}")
            elif actionType == "channel" or "type" in data:
                itemId = data.get("id")
                itemName = data.get("name","New Channel")
                newOverwrites = data.get("overwrites", [])
                
                if itemId and not isinstance(itemId, str): # Modify
                    toolDiff.append(f"*** '#{itemName}'")
                else: # Create
                    toolDiff.append(f"+​++ '#{itemName}'")
                
                for ow in newOverwrites:
                    targetId = ow.get("id")
                    target = guild.get_role(targetId) if guild else None
                    targetName = target.name if target else f"Unknown ({targetId})"
                    prefix = "@" if not target or isinstance(target, discord.Role) else ""
                    for p in ow.get('allow', []): toolDiff.append(f"+​++ {prefix}{targetName}: {p}")
                    for p in ow.get('deny', []): toolDiff.append(f"--​- {prefix}{targetName}: {p}")
            
            # check if adding this tool exceeds chunk limit (1900 to stay safe)
            potentialLength = sum(len(line)+1 for line in currentDiff)+sum(len(line)+1 for line in toolDiff)+len(sep)+20
            if potentialLength > 1900 and currentDiff:
                diffChunks.append("```diff\n"+"\n".join(currentDiff)+"\n"+sep+"\n```")
                currentDiff = toolDiff
            else:
                currentDiff.extend(toolDiff)
        
        if currentDiff:
            currentDiff.append(sep)
            diffChunks.append("```diff\n"+"\n".join(currentDiff)+"\n```")

        totalDiffLen = sum(len(chunk) for chunk in diffChunks)+(len(diffChunks)-1)*2
        
        if len(commentsText)+totalDiffLen+2 > 2000: return diffChunks if diffChunks else [commentsText] # omit comments if too long
        else:
            if not diffChunks: return [commentsText]
            firstChunk = commentsText+"\n\n"+diffChunks[0]
            return [firstChunk]+diffChunks[1:]
    
    ## BOT TOOLS
    @ErrorHandler
    async def listRoles(self, guild:discord.Guild):
        roles = []
        if not guild.roles: return []
        for role in guild.roles:
            perms = [name for name,value in role.permissions if value]
            roles.append({
                "name":role.name,
                "id":role.id,
                "position":role.position,
                "permissions":perms
            })
        roles.sort(key=lambda r: r["position"],reverse=True)
        return roles
    
    @ErrorHandler
    async def roleManagement(self, guild:discord.Guild, name:str, id:int=None, colour:str="#000000", hoist:bool=False, mentionable:bool=False, position:int=0, permissions:list=None, reason:str="Automated Action by Stagehand."):
        permsObj = discord.Permissions(**{p: True for p in permissions}) if permissions else discord.Permissions.none()
        colourHex = colour.replace("#", "")
        colourObj = discord.Color(int(colourHex, 16)) if colourHex else discord.Color.default()
        
        args = {
            "name": name,
            "permissions": permsObj,
            "colour": colourObj,
            "hoist": hoist,
            "mentionable": mentionable,
            "reason": reason
        }
        
        if not id:
            role = await guild.create_role(**args)
            if position > 0: await role.edit(position=position)
        else:
            role = guild.get_role(id)
            if role: await role.edit(**args, position=position)
        return role
        
    @ErrorHandler
    async def delete(self, guild:discord.Guild, id:int, type:discord.Role|discord.ChannelType, reason:str): # delete for channels/roles
        if isinstance(type,discord.Role): item = guild.get_role(id)
        elif isinstance(type,discord.ChannelType): item = guild.get_channel(id)
        await item.delete(reason=reason)

    @ErrorHandler
    async def listChannels(self, guild:discord.Guild):
        channels = []
        for channel in guild.channels:
            overwrites = []
            for target, overwrite in channel.overwrites.items():
                allow = [n for n, v in overwrite if v is True]
                deny = [n for n, v in overwrite if v is False]
                target_name = target.name if hasattr(target, "name") else str(target)
                overwrites.append({
                    "target": target_name,
                    "id": target.id,
                    "type": "role" if isinstance(target, discord.Role) else "member",
                    "allow": allow,
                    "deny": deny
                })
            channels.append({
                "name":channel.name,
                "id":channel.id,
                "type": str(channel.type).replace("ChannelType.",""),
                "category": channel.category.name if channel.category else "None",
                "overwrites": overwrites
            })
        channels.sort(key=lambda c: (c['category'], c['name']))
        return channels
    
    @ErrorHandler
    async def channelManagement(self, guild:discord.Guild, datatype:discord.ChannelType, name:str, id:int=None, topic:str=None, nsfw:bool=False, category:int=None, bitrate:int=64000, userLimit:int=0, slowmode:int=0, overwrites:list=None, reason:str="Automated Action by Stagehand.", position:int=None):
        channel = None
        targets = {}
        if overwrites:
            for ow in overwrites:
                target = guild.get_role(ow['id']) or guild.get_member(ow['id'])
                if target:
                    targets[target] = discord.PermissionOverwrite(**{p: True for p in ow.get('allow', [])}, **{p: False for p in ow.get('deny', [])})
        
        cat_obj = guild.get_channel(category) if category else None
        common = {"name": name, "overwrites": targets, "reason": reason, "category": cat_obj, "position": position}

        if not id: # Create
            if datatype == discord.ChannelType.text: channel = await guild.create_text_channel(**common, topic=topic, nsfw=nsfw, slowmode_delay=slowmode)
            elif datatype == discord.ChannelType.voice: channel = await guild.create_voice_channel(**common, bitrate=bitrate, user_limit=userLimit)
            elif datatype == discord.ChannelType.category: channel = await guild.create_category(name=name, overwrites=targets, reason=reason, position=position)
            elif datatype == discord.ChannelType.news: channel = await guild.create_news_channel(**common, topic=topic, nsfw=nsfw)
            elif datatype == discord.ChannelType.forum: channel = await guild.create_forum(**common, topic=topic, nsfw=nsfw)
            elif datatype == discord.ChannelType.stage_voice: channel = await guild.create_stage_channel(**common, topic=topic)
        else: # Modify
            channel = guild.get_channel(id)
            if channel:
                edit_map = {"name": name, "overwrites": targets, "reason": reason, "category": cat_obj, "position": position, "topic": topic, "nsfw": nsfw, "slowmode_delay": slowmode, "bitrate": bitrate, "user_limit": userLimit}
                final_edit = {k: v for k, v in edit_map.items() if hasattr(channel, k) or k in ["name", "overwrites", "reason", "category", "position"]}
                await channel.edit(**final_edit)
        return channel

async def setup(bot):
    await bot.add_cog(Robot(bot))
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
    def __init__(self,bot):
        self.bot = bot
        self.soul = ""
        
        with open("system/plan.md","r") as file:
            self.soul = file.read()

    @commands.Cog.listener()
    async def on_ready(self):
        await AsyncClient().chat( model="gemma4:e2b",messages=[{"role": "user","content": "Hello world!"}],think=False) # cold-star LLM

    @commands.Cog.listener()
    async def on_message(self,msg: discord.Message):
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

    @app_commands.command(name="plan",description="Instruct Stagehand to create an implementation plan")
    @app_commands.describe(instructions="Instructions to send")
    async def plan(self,interaction: discord.Interaction,instructions: str):
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

    async def getContext(self,msg: discord.Message):
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

    async def getTools(self,guild: discord.Guild = None):
        updated = self.soul+"\n\n## TOOLS\n"
        
        tools = ImplementationPlan.model_fields['actions']
        types = get_args(tools.annotation)[0]
        classes = get_args(types) or [types]

        for tool in classes:
            updated += f"- {tool.__name__}:\n"
            for field_name,field_info in tool.model_fields.items(): updated += f"\t- {field_name}: {field_info.description}\n"
        
        updated += "\n## ROLE PERMISSIONS\n"
        for name,value in iter(discord.Permissions.all()):  updated += f"- {name}:True/False\n"

        if guild:
            updated += "\n## EXISTING ROLES\n"
            roles = await self.listRoles(guild)
            for role in roles: updated += f"- {role['name']} (ID: {role['id']}): {','.join(role['permissions'])}\n"
        
        updated += "\n## USAGE GUIDELINES\n"
        updated += "1. 'name' must be a human-readable ROLE or CHANNEL name (e.g.,'Mod','Lounge').\n"
        updated += "2. NEVER put technical strings or permission names (like 'view_channel') in the 'name' field.\n"
        updated += "3. Avoid asking structural questions. Focus on the intent and providing the plan directly.\n"
        
        print(updated)
        return updated

    async def formatPlan(self,guild: discord.Guild,response: dict):
        commentsText = response.get("comments","")
        actionsList = response.get("actions",[])
        diffChunks = []
        currentDiff = []
        
        for action in actionsList:
            data = action.get("arguments",action)
            
            toolDiff = []
            if "datatype" in data or action.get("name") == "Delete":
                itemId = data.get("id")
                dataType = data.get("datatype","role")
                if dataType == "role":
                    role = guild.get_role(itemId)
                    name = role.name if role else f"Unknown ({itemId})"
                    toolDiff.extend(["---",f"- '＠{name}'"])
                else: # channel
                    channel = guild.get_channel(itemId)
                    name = channel.name if channel else f"Unknown ({itemId})"
                    toolDiff.extend(["---",f"- '#{name}'"])
            elif "permissions" in data or action.get("name") == "RolePermissions":
                itemId = data.get("id")
                itemName = data.get("name","New Role")
                newPerms = data.get("permissions",[])
                
                toolDiff.append("---")
                if itemId and itemId != "RolePermissions": # Modify Role
                    oldRole = guild.get_role(itemId)
                    toolDiff.append(f"+ '＠{itemName}'")
                    if oldRole:
                        oldPerms = [n for n,v in oldRole.permissions if v]
                        added = [p for p in newPerms if p not in oldPerms]
                        removed = [p for p in oldPerms if p not in newPerms]
                        if added or removed:
                            toolDiff.append("Permissions:")
                            for p in added: toolDiff.append(f"+ {p}")
                            for p in removed: toolDiff.append(f"- {p}")
                else: # create Role
                    toolDiff.append(f"+ '＠{itemName}'")
                    if newPerms:
                        toolDiff.append("Permissions:")
                        for p in newPerms: toolDiff.append(f"+ {p}")
            elif "type" in data or action.get("name") == "ChannelManagement":
                itemId = data.get("id")
                itemName = data.get("name","New Channel")
                
                toolDiff.append("---")
                toolDiff.append(f"+ '#{itemName}'")
            
            # check if adding this tool exceeds chunk limit (1900 to stay safe)
            potentialLength = sum(len(line)+1 for line in currentDiff)+sum(len(line)+1 for line in toolDiff)+20
            if potentialLength > 1900 and currentDiff:
                diffChunks.append("```diff\n"+"\n".join(currentDiff)+"\n```")
                currentDiff = toolDiff
            else:
                currentDiff.extend(toolDiff)

        if currentDiff:
            diffChunks.append("```diff\n"+"\n".join(currentDiff)+"\n```")

        totalDiffLen = sum(len(chunk) for chunk in diffChunks)+(len(diffChunks)-1)*2
        
        if len(commentsText)+totalDiffLen+2 > 2000: return diffChunks if diffChunks else [commentsText] # omit comments if too long
        else:
            if not diffChunks: return [commentsText]
            firstChunk = commentsText+"\n\n"+diffChunks[0]
            return [firstChunk]+diffChunks[1:]
    
    ## BOT TOOLS
    @ErrorHandler
    async def listRoles(self,guild:discord.Guild):
        roles = []
        if not guild.roles: return []
        for role in guild.roles:
            perms = [name for name,value in role.permissions if value]
            roles.append({
                "name": role.name,
                "id": role.id,
                "position": role.position,
                "permissions": perms
            })
        roles.sort(key=lambda r: r["position"],reverse=True)
        return roles
    
    @ErrorHandler
    async def rolePermissions(self,guild:discord.Guild,id:int):
        role = guild.get_role(id)
        return role.permissions
    
    @ErrorHandler
    async def roleModify(self,guild:discord.Guild,reason:str,name:str,id:int,colour:discord.Colour=None,hoist:bool=False,mentionable:bool=False,**permissions:discord.Permissions):
        permissions = permissions if permissions != None else discord.Permissions.none()
        colour = colour if colour != None else discord.Color.default()
        args = [name,permissions,colour,hoist,mentionable,reason]
        if not id: role = await guild.create_role(*args)
        else: role = await guild.get_role(id).edit(*args) # if id exist,then modify instead of create
        return role
        
    @ErrorHandler
    async def delete(self,guild:discord.Guild,id:int,datatype:discord.Role|discord.ChannelType,reason:str):
        if isinstance(datatype,discord.Role): item = guild.get_role(id)
        elif isinstance(datatype,discord.ChannelType): item = guild.get_channel(id)
        await item.delete(reason=reason)

async def setup(bot):
    await bot.add_cog(Robot(bot))
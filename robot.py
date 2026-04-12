import ast
import inspect
import json
import asyncio
import traceback
import os
from typing import Optional,get_args, Literal
import discord
from discord import app_commands
from discord.ext import commands
from ollama import ChatResponse
from ollama import AsyncClient
from dotenv import load_dotenv
from pydantic import BaseModel

class Robot(commands.Cog):
    def __init__(self, bot):
        self.bot:discord.ClientUser = bot
        self.model="gemma4:e2b"
        
        with open("system/decision.md","r") as file:
            self.decision_prompt = file.read()
        with open("system/roles.md","r") as file:
            self.roles_prompt = file.read()
        with open("system/channels.md","r") as file:
            self.channels_prompt = file.read()

    @commands.Cog.listener()
    async def on_ready(self):
        await AsyncClient().chat(model=self.model, messages=[{"role":"user","content":"Hello world!"}],think=False) # cold-start LLM

    async def pipeline(self, msg_or_interaction: discord.Message | discord.Interaction, instructions: str = None, context_messages: list = None):
        guild = msg_or_interaction.guild
        
        # 1. Ask Decision LLM
        decision_messages = [{"role": "system", "content": self.decision_prompt}]
        if context_messages: decision_messages.extend(context_messages)
        if instructions: decision_messages.append({"role": "user", "content": instructions})
            
        from models import DecisionPlan, RoleImplementationPlan, ChannelImplementationPlan
        
        decision_reply = await AsyncClient().chat(model=self.model, messages=decision_messages, think=False, format=DecisionPlan.model_json_schema())
        try:
            decision = json.loads(decision_reply.message.content)
            roles_needed = decision.get("rolesNeeded", False)
            channels_needed = decision.get("channelsNeeded", False)
        except:
            roles_needed = True
            channels_needed = True
        
        last_message = None
        
        # Helper to repeatedly thread replies
        async def send_sequence(parts, reply_target):
            first = None
            for i, text in enumerate(parts):
                if isinstance(msg_or_interaction, discord.Interaction) and reply_target is None and i == 0:
                    first = await msg_or_interaction.followup.send(text, wait=True)
                elif reply_target is not None and hasattr(reply_target, "reply"):
                    first = await reply_target.reply(text)
                elif isinstance(msg_or_interaction, discord.Message) and reply_target is None and i == 0:
                    first = await msg_or_interaction.reply(text)
                elif hasattr(msg_or_interaction, "channel"):
                    first = await msg_or_interaction.channel.send(text)
                else: 
                    # fallback
                    first = await msg_or_interaction.channel.send(text)
                reply_target = first
            return first

        # 2. Roles
        if roles_needed:
            roles_context = await self.getPlan(guild, "role")
            role_msgs = [{"role": "system", "content": roles_context}]
            if context_messages: role_msgs.extend(context_messages)
            if instructions: role_msgs.append({"role": "user", "content": instructions})
            
            role_reply = await AsyncClient().chat(model=self.model, messages=role_msgs, think=True, format=RoleImplementationPlan.model_json_schema())
            role_parts = await self.processResponse(guild, role_reply.message.content, model=RoleImplementationPlan)
            last_message = await send_sequence(role_parts, None)
            
        # 3. Channels
        if channels_needed:
            channels_context = await self.getPlan(guild, "channel")
            channel_msgs = [{"role":"system", "content": channels_context}]
            if context_messages: channel_msgs.extend(context_messages)
            if instructions: channel_msgs.append({"role":"user", "content": instructions})
            
            channel_reply = await AsyncClient().chat(model=self.model, messages=channel_msgs, think=True, format=ChannelImplementationPlan.model_json_schema())
            channel_parts = await self.processResponse(guild, channel_reply.message.content, model=ChannelImplementationPlan)
            
            reply_to = last_message
            if reply_to is None and isinstance(msg_or_interaction, discord.Interaction):
                # We haven't sent anything yet, so we should respond to the interaction
                # If we pass None, our send_sequence will use followup.send(..., wait=True) which is correct
                reply_to = None
            
            await send_sequence(channel_parts, reply_to)

        if not roles_needed and not channels_needed:
            await send_sequence(["The Decision LLM determined no roles or channels needed to be created."], None)

    @commands.Cog.listener()
    async def on_message(self, msg: discord.Message):
        if not self.bot.is_ready(): return
        if msg.author == self.bot.user: return
        if msg.reference and isinstance(msg.reference.resolved,discord.Message):
            replied = msg.reference.resolved
            if replied.author == self.bot.user:
                context = await self.getContext(msg)
                async with msg.channel.typing():
                    await self.pipeline(msg, context_messages=context)

    @app_commands.command(name="plan", description="Instruct Stagehand to create an implementation plan")
    @app_commands.describe(instructions="Instructions to send")
    async def plan(self, interaction: discord.Interaction, instructions: str):
        await interaction.response.defer(thinking=True)
        await self.pipeline(interaction, instructions=instructions)

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
    
    @commands.command(name="test")
    @commands.is_owner()
    async def test(self, ctx:discord.Interaction):
        test = """{'comments': "The plan will hide the general channel from @everyone by denying them the ability to view and read messages. This will be done by setting overwrites on the 'general' channel for the '@everyone' role.", 'actions': [{'action': 'channel', 'id': None, 'name': 'general', 'type': 'text', 'topic': 'General discussion.', 'nsfw': False, 'category': 1492042343661047860, 'position': None, 'bitrate': 64000, 'userLimit': 0, 'slowmode': 0, 'overwrites': {1492042343115919493: ['view_channel', 'read_messages']}, 'reason': 'Hiding the general channel from @everyone as requested.'}]}"""
        parsed = ast.literal_eval(test)
        parsed["actions"] = sorted(parsed["actions"], key=lambda x: {"role": 0, "channel": 1}.get(x["action"], 99))
        for _,args in enumerate(parsed["actions"]):
            datatype = args.pop("action")
            await (self.channelManagement(guild=ctx.guild, **args) if datatype == "channel" else self.roleManagement(guild=ctx.guild, **args))

    ## PRELIMINARIES
    def ErrorHandler(func):
        async def wrapper(*args,**kwargs):
            try:
                if inspect.iscoroutinefunction(func): return await func(*args,**kwargs)
                return func(*args,**kwargs)
            except discord.Forbidden as e: return f"403: Forbidden\nBot does not have permissions: {e}"
            except discord.HTTPException as e: return f"409: Bad Request\nBot failed to perform action: {e}"
            except Exception as e:
                traceback.print_exc()
                return f"500: Internal Server Error\nUnexpected failure {e}"
        return wrapper

    def resolveId(self, guild: discord.Guild, ref: int|str|None, datatype: Literal["role", "channel"]):
        if not ref or isinstance(ref, int): return ref
        if isinstance(ref, str) and ref.isdigit(): return int(ref)
        
        # Resolve by name
        ref_low = ref.lower().lstrip("@#")
        if datatype == "role":
            if ref_low == "everyone": return guild.default_role.id
            role = discord.utils.get(guild.roles, name=ref) or discord.utils.find(lambda r: r.name.lower() == ref_low, guild.roles)
            if role: return role.id
        else: # channel
            channel = discord.utils.get(guild.channels, name=ref) or discord.utils.find(lambda c: c.name.lower() == ref_low, guild.channels)
            if channel: return channel.id
        return ref

    async def getContext(self, msg: discord.Message):
        # We don't prepend the soul to the context here anymore, since we dynamically select the system prompt.
        messages = [{"role": ("assistant" if msg.author == self.bot.user else "user"),"content": msg.content}]
        current = msg

        while current.reference and current.reference.message_id:
            if isinstance(current.reference.resolved,discord.Message): current = current.reference.resolved
            else:
                try: current = await msg.channel.fetch_message(current.reference.message_id)
                except discord.NotFound: break
            messages.append({"role": ("assistant" if current.author == self.bot.user else "user"),"content": current.content})
        
        messages.reverse()
        return messages

    async def getPlan(self, guild: discord.Guild, plan_type: Literal["role", "channel"]) -> str:
        prompt = self.roles_prompt if plan_type == "role" else self.channels_prompt
        updated = prompt + "\n\n## TOOLS\n"
        
        from models import RoleImplementationPlan, ChannelImplementationPlan
        model = RoleImplementationPlan if plan_type == "role" else ChannelImplementationPlan
        tools = model.model_fields['actions']
        types = get_args(tools.annotation)[0]
        classes = get_args(types) or [types]

        for tool in classes:
            updated += f"- {tool.__name__}:\n"
            for field_name,field_info in tool.model_fields.items(): updated += f"\t- {field_name}: {field_info.description}\n"
        
        if guild:
            if plan_type == "role":
                updated += "\n## EXISTING ROLES\n"
                roles = await self.listRoles(guild)
                if isinstance(roles, list):
                    for role in roles: updated += f"- Name: '{role['name']}' (ID: {role['id']}): Allowed: {', '.join(role['allowed'])} | Denied: {', '.join(role['denied'])}\n"
                else: updated += f"Error fetching roles: {roles}\n"
            
            if plan_type == "channel":
                updated += "\n## EXISTING CATEGORIES\n"
                channels = await self.listChannels(guild)
                if isinstance(channels, list):
                    for ch in channels:
                        if ch['type'] == "category":
                            updated += f"- Name: '{ch['name']}' (ID: {ch['id']})\n"
                    
                    updated += "\n## EXISTING CHANNELS\n"
                    for ch in channels:
                        if ch['type'] != "category":
                            p_text = ""
                            for ow in ch['overwrites']:
                                p_text += f"{ow['target']}({ow['type']}): -{','.join(ow['deny'])} | "
                            updated += f"- Name: '{ch['name']}' (Type: {ch['type']}, ID: {ch['id']}): {p_text}\n"
                else: updated += f"Error fetching channels: {channels}\n"
        
        print(updated)
        return updated

    async def processResponse(self, guild: discord.Guild, content: str, model=None):
        try:
            # Extract JSON if present within conversational text
            start = content.find('{')
            end = content.rfind('}') + 1
            if start != -1 and end != -1:
                json_part = content[start:end]
                data = json.loads(json_part)
                # Check if it's a valid plan
                if "actions" in data or "comments" in data:
                    # Pre-resolve string IDs before Pydantic validation
                    for act in data.get("actions", []):
                        dtype = "role" if act.get("action") == "role" else "channel"
                        
                        if "id" in act: act["id"] = self.resolveId(guild, act["id"], dtype)
                        if "category" in act: act["category"] = self.resolveId(guild, act["category"], "channel")
                        if "overwrites" in act:
                            new_ow = {}
                            for target_ref, deny_list in act["overwrites"].items():
                                resolved = self.resolveId(guild, target_ref, "role")
                                new_ow[resolved] = deny_list
                            act["overwrites"] = new_ow

                    if model:
                        plan = model(**data)
                        response = plan.model_dump()
                    else:
                        response = data
                    
                    seen = set()
                    unique = []
                    for act in response.get("actions", []):
                        act_id = act.get("id")
                        act_type = act.get("action")
                        key = (act_id, act_type)
                        if act_id and key in seen: continue
                        if act_id: seen.add(key)
                        unique.append(act)
                    response["actions"] = unique
                    print(response)
                    return await self.formatPlan(guild, response)
            
            # If not JSON or not a plan, treat as text and chunk it
            return [content[i:i+1900] for i in range(0, len(content), 1900)]
        except:
            # Fallback to text chunking
            return [content[i:i+1900] for i in range(0, len(content), 1900)]

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
            elif actionType == "role" or any(k in data for k in ["deny", "colour", "hoist", "mentionable"]):
                itemId = data.get("id")
                itemName = data.get("name","New Role")
                deny_list = data.get("deny",[])
                
                if itemId and not isinstance(itemId, str): # Modify Role
                    oldRole = guild.get_role(itemId)
                    toolDiff.append(f"*** '@{itemName}'")
                    if oldRole:
                        # Logic: show what changed from the current state to the new 'deny' based state
                        # Or simply show what is specifically being DENIED now.
                        for p in deny_list: toolDiff.append(f"--​- {p} (DENIED)")
                else: # create Role
                    toolDiff.append(f"+​++ '@{itemName}' (All Allowed by Default)")
                    for p in deny_list: toolDiff.append(f"--​- {p} (DENIED)")
            elif actionType == "channel" or any(k in data for k in ["topic", "nsfw", "overwrites", "userLimit"]):
                itemId = data.get("id")
                itemName = data.get("name","New Channel")
                newOverwrites = data.get("overwrites", [])
                
                if itemId and not isinstance(itemId, str): # Modify
                    toolDiff.append(f"*** '#{itemName}'")
                else: # Create
                    toolDiff.append(f"+​++ '#{itemName}'")
                
                for targetId, denyList in newOverwrites.items():
                    target = guild.get_role(targetId) if guild else None
                    targetName = target.name if target else f"Unknown ({targetId})"
                    prefix = "@" if not target or isinstance(target, discord.Role) else ""
                    for p in denyList: toolDiff.append(f"--​- {prefix}{targetName}: {p} (DENIED)")
            
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
            if role.name != "Stagehand":
                allowed = [name for name,value in role.permissions if value]
                denied = [name for name,value in role.permissions if not value]
                roles.append({
                    "name":role.name,
                    "id":role.id,
                    "position":role.position,
                    "allowed":allowed,
                    "denied":denied
                })
        roles.sort(key=lambda r: r["position"],reverse=True)
        return roles
    
    @ErrorHandler
    async def roleManagement(self, guild:discord.Guild, name:str, id:int|str|None=None, colour:str="#000000", hoist:bool=False, mentionable:bool=False, position:int=0, deny:list=None, reason:str="Automated Action by Stagehand."):
        if not id and name.lower().lstrip("@") == "everyone": id = guild.default_role.id
        id = self.resolveId(guild, id, "role")
        
        permsObj = discord.Permissions.all()
        if deny:
            for p in deny:
                if hasattr(permsObj, p): setattr(permsObj, p, False)
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
        
        if not id or isinstance(id, str):
            role = await guild.create_role(**args)
            if position > 0: await role.edit(position=position)
        else:
            role = guild.get_role(id)
            if role:
                if role.is_default(): await role.edit(permissions=permsObj, reason=reason)
                else: await role.edit(**args, position=position)
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
                name = target.name if hasattr(target, "name") else str(target)
                overwrites.append({
                    "target": name,
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
    async def channelManagement(self, guild:discord.Guild, type:discord.ChannelType|str|int, name:str, id:int|str|None=None, topic:str=None, nsfw:bool=False, category:int|str|None=None, bitrate:int=64000, userLimit:int=0, slowmode:int=0, overwrites:dict=None, reason:str="Automated Action by Stagehand.", position:int=None):
        # Resolve ID and Category
        id = self.resolveId(guild, id, "channel")
        category = self.resolveId(guild, category, "channel")
        
        # Resolve Channel Type from int or str
        if isinstance(type, str):
            mapping = {
                "text": discord.ChannelType.text,
                "voice": discord.ChannelType.voice,
                "category": discord.ChannelType.category,
                "news": discord.ChannelType.news,
                "forum": discord.ChannelType.forum,
                "stage": discord.ChannelType.stage_voice,
                "public_thread": discord.ChannelType.public_thread,
                "private_thread": discord.ChannelType.private_thread,
                "announcement": discord.ChannelType.news,
            }
            type = mapping.get(type.lower(), discord.ChannelType.text)
        elif isinstance(type, int):
            type = discord.ChannelType(type)

        channel = None
        targets = {}
        if overwrites:
            for target_id, denied in overwrites.items():
                target = guild.get_role(target_id) or guild.get_member(target_id)
                if target:
                    ov = discord.PermissionOverwrite()
                    for p_name, _ in discord.Permissions.all():
                        if hasattr(ov, p_name): setattr(ov, p_name, True)
                    
                    for p in denied:
                        if hasattr(ov, p): setattr(ov, p, False)
                    targets[target] = ov
        
        cat_obj = guild.get_channel(category) if category else None
        common = {"name": name, "overwrites": targets, "reason": reason, "category": cat_obj, "position": position}

        if not id or isinstance(id, str): # Create
            if type == discord.ChannelType.text: channel = await guild.create_text_channel(**common, topic=topic, nsfw=nsfw, slowmode_delay=slowmode)
            elif type == discord.ChannelType.voice: channel = await guild.create_voice_channel(**common, bitrate=bitrate, user_limit=userLimit)
            elif type == discord.ChannelType.category: channel = await guild.create_category(name=name, overwrites=targets, reason=reason, position=position)
            elif type == discord.ChannelType.news: channel = await guild.create_news_channel(**common, topic=topic, nsfw=nsfw)
            elif type == discord.ChannelType.forum: channel = await guild.create_forum(**common, topic=topic, nsfw=nsfw)
            elif type == discord.ChannelType.stage_voice: channel = await guild.create_stage_channel(**common, topic=topic)
        else: # Modify
            channel = guild.get_channel(id)
            if channel:
                edit_map = {"name": name, "overwrites": targets, "reason": reason, "category": cat_obj, "position": position, "topic": topic, "nsfw": nsfw, "slowmode_delay": slowmode, "bitrate": bitrate, "user_limit": userLimit}
                final_edit = {k: v for k, v in edit_map.items() if hasattr(channel, k) or k in ["name", "overwrites", "reason", "category", "position"]}
                await channel.edit(**final_edit)
        return channel

class ImplementationButtons(discord.ui.View):
    def __init__(self, cog:Robot, plan:dict, timeout = 300):
        super().__init__(timeout=timeout)
        self.cog = cog
        self.plan = plan

    @discord.ui.button(label="Proceed", style=discord.ButtonStyle.blurple)
    async def proceed(self, interaction:discord.Interaction, button:discord.ui.Button):
        await interaction.response.defer()
        actions = sorted(self.plan.get("actions", []), key=lambda x: {"role": 0, "channel": 1}.get(x.get("action", ""), 99))
        for args in actions:
            args = dict(args)  # avoid mutating the stored plan
            datatype = args.pop("action")
            if datatype == "channel": await self.cog.channelManagement(guild=interaction.guild, **args)
            else: await self.cog.roleManagement(guild=interaction.guild, **args)
        await interaction.followup.send("Implementation complete.", ephemeral=True)
    
async def setup(bot):
    cog = Robot(bot)
    await bot.add_cog(cog)

    @bot.tree.context_menu(name="Finalize Implementation")
    async def implement(interaction: discord.Interaction, msg: discord.Message):
        await interaction.response.defer()
        
        # Parse the raw JSON into a plan before formatting
        raw = msg.content
        plan = None
        try:
            start = raw.find('{')
            end = raw.rfind('}') + 1
            if start != -1 and end > start:
                import json as _json
                data = _json.loads(raw[start:end])
                if "actions" in data or "comments" in data:
                    from models import RoleImplementationPlan, ChannelImplementationPlan
                    # Determine type loosely
                    is_role = False
                    for act in data.get("actions", []):
                        if act.get("action") == "role":
                            is_role = True
                            break
                    model = RoleImplementationPlan if is_role else ChannelImplementationPlan
                    plan = model(**data).model_dump()
        except Exception: pass

        if plan:
            view = ImplementationButtons(cog=cog, plan=plan)
            await interaction.followup.send("Are you sure you want to deploy this implementation?", view=view)
        else:
            await interaction.followup.send("Could not parse a valid plan from this message.", ephemeral=True)